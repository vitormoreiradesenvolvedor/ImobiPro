"""Validadores de documento brasileiro.

Contrato assinado com CPF inválido é problema jurídico, não erro de digitação
por isso a checagem de dígito verificador é feita no servidor.
"""

import re

from django.core.exceptions import ValidationError


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _digito(base: str, pesos: list) -> str:
    soma = sum(int(digito) * peso for digito, peso in zip(base, pesos, strict=True))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cpf_valido(cpf: str) -> bool:
    cpf = somente_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    primeiro = _digito(cpf[:9], list(range(10, 1, -1)))
    segundo = _digito(cpf[:9] + primeiro, list(range(11, 1, -1)))
    return cpf.endswith(primeiro + segundo)


def cnpj_valido(cnpj: str) -> bool:
    cnpj = somente_digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    primeiro = _digito(cnpj[:12], pesos1)
    segundo = _digito(cnpj[:12] + primeiro, pesos2)
    return cnpj.endswith(primeiro + segundo)


def validar_cpf_cnpj(valor: str) -> str:
    """Normaliza para dígitos e valida. Levanta ValidationError se inválido."""

    documento = somente_digitos(valor)

    if len(documento) == 11:
        if not cpf_valido(documento):
            raise ValidationError("CPF inválido.")
    elif len(documento) == 14:
        if not cnpj_valido(documento):
            raise ValidationError("CNPJ inválido.")
    else:
        raise ValidationError("Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")

    return documento


def validar_cep(valor: str) -> str:
    cep = somente_digitos(valor)
    if cep and len(cep) != 8:
        raise ValidationError("CEP deve ter 8 dígitos.")
    return cep
