"""Servidor de síntese de voz para a gravação do vídeo.

Carrega o Chatterbox uma vez e fica lendo pedidos do stdin, uma linha JSON por
fala: {"texto": "...", "arquivo": "/caminho/saida.wav"}. Responde outra linha
JSON com a duração do áudio gerado.

Existe por causa do custo de carga: o modelo leva dezenas de segundos para subir
na GPU, e o roteiro tem mais de cinquenta falas. Carregar uma vez por fala
levaria mais tempo do que gravar o vídeo inteiro.

Três cuidados que separam uma locução usável de uma que troca de sotaque no meio
da frase:

1. **Referência de voz em português.** A voz embutida no `conds.pt` do modelo é
   inglesa. Sem um áudio de referência em pt-BR, o modelo escorrega para o
   sotaque de origem e, em frases longas, chega a trocar de idioma.
2. **Uma sentença por geração.** Texto longo aumenta a chance de alucinação. As
   sentenças são sintetizadas separadamente e emendadas com uma pausa curta.
3. **Corte da cauda.** O modelo costuma deixar um estalo depois da última
   sílaba. O silêncio final é aparado e sobra um fade curto.

Uso (o Node cuida disso; a linha abaixo serve para depurar):

    echo '{"texto":"Olá","arquivo":"/tmp/ola.wav"}' | python scripts/voz_servidor.py <modelo> [referencia.wav]
"""

import json
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

import torch  # noqa: E402
import torchaudio  # noqa: E402
from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: E402

# Narração comercial pede fala firme e sem drama: exagero baixo e temperatura
# baixa deixam a leitura estável de uma frase para a outra.
EXAGERO = 0.4
PESO_CFG = float(os.getenv("VOZ_CFG", "0.5"))
TEMPERATURA = 0.5
SEMENTE = 1986
MEIA_PRECISAO = os.getenv("VOZ_FP16") == "1"

# Pausa entre as sentenças de uma mesma fala.
PAUSA = 0.18
# Silêncio abaixo deste nível é considerado cauda e sai fora.
LIMIAR_SILENCIO = 0.012
FADE = 0.09


# Siglas que o modelo lê como se fossem palavras. A grafia à direita é a
# pronúncia letra a letra em português, que é como um locutor leria.
SIGLAS = {
    "IPTU": "i pê tê u",
    "SLA": "esse éle a",
    "PDF": "pê dê éfe",
    "CPF": "cê pê éfe",
    "CNPJ": "cê ene pê jota",
    "CNAB": "cê ene a bê",
    "CRM": "cê erre eme",
    "API": "a pê i",
    "LGPD": "éle gê pê dê",
}


def expandir_siglas(texto):
    """Troca a sigla pela pronúncia soletrada, preservando o resto da frase."""

    def trocar(achado):
        return SIGLAS[achado.group(0)]

    padrao = r"\b(" + "|".join(sorted(SIGLAS, key=len, reverse=True)) + r")\b"
    return re.sub(padrao, trocar, texto)


# Trecho longo demais estoura a memória de uma GPU de 4 GB e aumenta a chance
# de o modelo alucinar. Acima disto, a sentença é partida na vírgula.
# O pico de memória acompanha o tanto de áudio gerado de uma vez. Setenta
# caracteres por trecho é o que cabe com folga numa placa de 4 GB, contando que
# a biblioteca sempre roda o transformer com lote dobrado.
LIMITE_TRECHO = int(os.getenv("VOZ_LIMITE_TRECHO", "70"))


def _partir(sentenca):
    if len(sentenca) <= LIMITE_TRECHO:
        return [sentenca]

    trechos, atual = [], ""
    for pedaco in re.split(r"(?<=,)\s+", sentenca):
        if atual and len(atual) + len(pedaco) > LIMITE_TRECHO:
            trechos.append(atual.strip())
            atual = pedaco
        else:
            atual = f"{atual} {pedaco}".strip()
    if atual:
        trechos.append(atual.strip())
    return trechos


def sentencas(texto):
    """Quebra a fala em sentenças, mantendo a pontuação que dá a entonação."""

    partes = re.split(r"(?<=[.!?:])\s+", texto.strip())
    return [trecho for parte in partes if parte.strip() for trecho in _partir(parte.strip())]


def aparar(audio, taxa):
    """Tira silêncio e estalo das pontas, e fecha com um fade curto.

    A cauda do modelo nem sempre é alta: às vezes é um estalo baixo, logo depois
    da última sílaba, que o corte por amostra isolada não pega. Por isso o fim é
    procurado por energia em janelas de 20 ms, e o último pedaço sai fora mesmo
    quando parece silêncio.
    """

    onda = audio.squeeze(0)
    janela = max(1, int(0.02 * taxa))

    quadros = onda[: (onda.shape[0] // janela) * janela].reshape(-1, janela)
    if quadros.shape[0] == 0:
        return audio

    energia = quadros.pow(2).mean(dim=1).sqrt()
    com_voz = (energia > LIMIAR_SILENCIO).nonzero()
    if com_voz.numel() == 0:
        return audio

    inicio = max(0, (int(com_voz[0].item()) - 1) * janela)
    # Uma janela a menos no fim: é onde o estalo mora.
    fim = min(onda.shape[0], (int(com_voz[-1].item()) + 1) * janela)
    cortado = onda[inicio:fim].clone()

    amostras_fade = min(int(FADE * taxa), cortado.shape[0])
    if amostras_fade > 0:
        cortado[-amostras_fade:] *= torch.linspace(1.0, 0.0, amostras_fade)
    return cortado.unsqueeze(0)


def _gerar(modelo, sentenca, dispositivo):
    """Gera um trecho, com uma segunda tentativa depois de limpar a GPU.

    Quatro gigabytes de VRAM não sobram muito depois do modelo carregado: a
    memória fragmenta ao longo da gravação e uma frase falha do nada. Limpar e
    repetir resolve sem derrubar a locução inteira.
    """

    for tentativa in (1, 2):
        try:
            with torch.inference_mode():
                return modelo.generate(
                    sentenca,
                    language_id="pt",
                    exaggeration=EXAGERO,
                    cfg_weight=PESO_CFG,
                    temperature=TEMPERATURA,
                )
        except torch.cuda.OutOfMemoryError:
            if tentativa == 2 or dispositivo != "cuda":
                raise
            torch.cuda.empty_cache()
        finally:
            if dispositivo == "cuda":
                torch.cuda.empty_cache()
    raise RuntimeError("memória insuficiente na GPU")


def _meia_precisao_nos_conds(modelo):
    """Converte para fp16 os tensores de condicionamento do transformer."""

    condicao = getattr(getattr(modelo, "conds", None), "t3", None)
    if condicao is None:
        return

    for nome in dir(condicao):
        if nome.startswith("_"):
            continue
        valor = getattr(condicao, nome, None)
        if torch.is_tensor(valor) and valor.is_floating_point():
            setattr(condicao, nome, valor.half())


def principal():
    pasta = sys.argv[1]
    referencia = sys.argv[2] if len(sys.argv) > 2 else None

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    modelo = ChatterboxMultilingualTTS.from_local(pasta, device=dispositivo)

    # Meia precisão no transformer: em fp32 o modelo sozinho ocupa 3,4 GB e não
    # cabe com folga numa placa de 4 GB, e as falas longas falham no meio da
    # gravação. O decoder continua em fp32, que é onde a qualidade do áudio é
    # decidida.
    if dispositivo == "cuda" and MEIA_PRECISAO:
        modelo.t3 = modelo.t3.half()
        torch.cuda.empty_cache()

    # A referência é embutida uma única vez: refazer o embed a cada fala custa
    # memória de GPU (4 GB não sobram para isso) e não muda o resultado.
    if referencia:
        modelo.prepare_conditionals(referencia, exaggeration=EXAGERO)

    # Os vetores de condicionamento nascem em fp32: com o transformer em fp16, a
    # multiplicação quebra por tipos diferentes. Convertidos aqui, depois de a
    # referência já ter sido embutida.
    if dispositivo == "cuda" and MEIA_PRECISAO:
        _meia_precisao_nos_conds(modelo)
    print(
        json.dumps({"pronto": True, "dispositivo": dispositivo, "referencia": referencia}),
        flush=True,
    )

    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue

        pedido = json.loads(linha)
        try:
            pedacos = []
            for indice, sentenca in enumerate(sentencas(expandir_siglas(pedido["texto"]))):
                # Semente fixa por sentença: regravar o vídeo com o mesmo texto
                # devolve exatamente o mesmo áudio.
                torch.manual_seed(SEMENTE + indice)
                gerado = _gerar(modelo, sentenca, dispositivo)
                pedacos.append(aparar(gerado.cpu(), modelo.sr))
                pedacos.append(torch.zeros(1, int(modelo.sr * PAUSA)))

            audio = torch.cat(pedacos[:-1], dim=1)
            torchaudio.save(pedido["arquivo"], audio, modelo.sr)
            print(json.dumps({"ok": True, "duracao": audio.shape[1] / modelo.sr}), flush=True)
        except Exception as erro:  # a gravação continua sem esta fala
            print(json.dumps({"ok": False, "erro": str(erro)}), flush=True)


if __name__ == "__main__":
    principal()
