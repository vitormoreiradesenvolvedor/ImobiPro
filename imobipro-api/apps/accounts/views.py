from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import Tenant
from apps.accounts.permissions import PodeGerenciarUsuarios
from apps.accounts.serializers import (
    CadastroSerializer,
    ConfirmacaoResetSenhaSerializer,
    IdentidadePublicaSerializer,
    LoginSerializer,
    PerfilSerializer,
    SolicitacaoResetSenhaSerializer,
    UsuarioCriacaoSerializer,
    UsuarioSerializer,
)
from apps.core.mixins import TenantQuerySetMixin

Usuario = get_user_model()


class AccessSerializer(serializers.Serializer):
    """Só documenta a resposta de /refresh/ o refresh vive no cookie."""

    access = serializers.CharField(read_only=True)


def _gravar_cookie_refresh(response, refresh):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )
    return response


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ → {access, user}; refresh vai em cookie HttpOnly."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    # Só o balde de login: navegar pela vitrine pública não pode consumir o
    # limite de quem precisa entrar no sistema.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        resposta = super().post(request, *args, **kwargs)
        refresh = resposta.data.pop("refresh", None)
        if refresh:
            _gravar_cookie_refresh(resposta, refresh)
        return resposta


@extend_schema(
    request=CadastroSerializer,
    responses={201: OpenApiResponse(description="Conta criada e sessão aberta")},
)
class CadastroView(APIView):
    """POST /api/v1/auth/cadastro/ → cria imobiliária + admin e já entra.

    A resposta tem o mesmo formato do login ({access, user} e refresh em
    cookie), para a SPA seguir direto ao painel sem pedir a senha de novo.
    """

    serializer_class = CadastroSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "cadastro"

    def post(self, request):
        serializer = CadastroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()

        refresh = LoginSerializer.get_token(usuario)
        resposta = Response(
            {
                "access": str(refresh.access_token),
                "user": PerfilSerializer(usuario, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )
        return _gravar_cookie_refresh(resposta, str(refresh))


@extend_schema(
    request=None,
    responses={200: AccessSerializer, 401: OpenApiResponse(description="Sessão inválida")},
)
class RefreshView(APIView):
    """Renova o access token lendo o refresh do cookie nunca do corpo.

    Balde próprio: a SPA renova a sessão a cada carga de página, e esse tráfego
    não pode esgotar o limite anônimo compartilhado com a vitrine pública.
    """

    serializer_class = AccessSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refresh"

    def post(self, request):
        bruto = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not bruto:
            return Response(
                {"detail": "Sessão expirada.", "code": "sem_refresh", "campos": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(bruto)
            access = str(refresh.access_token)
            if settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"]:
                refresh.blacklist()
                usuario = Usuario.objects.get(pk=refresh["user_id"])
                novo = LoginSerializer.get_token(usuario)
                resposta = Response({"access": str(novo.access_token)})
                return _gravar_cookie_refresh(resposta, str(novo))
        except (TokenError, Usuario.DoesNotExist):
            return Response(
                {"detail": "Sessão inválida.", "code": "refresh_invalido", "campos": {}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response({"access": access})


@extend_schema(
    request=None, responses={204: OpenApiResponse(description="Sessão encerrada")}
)
class LogoutView(APIView):
    """Invalida o refresh (blacklist) e apaga o cookie."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        bruto = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if bruto:
            try:
                RefreshToken(bruto).blacklist()
            except TokenError:
                pass

        resposta = Response(status=status.HTTP_204_NO_CONTENT)
        resposta.delete_cookie(
            settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH
        )
        return resposta


@extend_schema(responses=PerfilSerializer)
class PerfilView(APIView):
    """GET /api/v1/auth/me/ usuário, tenant e capacidades do papel."""

    serializer_class = PerfilSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PerfilSerializer(request.user).data)


@extend_schema(
    request=SolicitacaoResetSenhaSerializer,
    responses={202: OpenApiResponse(description="Solicitação registrada")},
)
class SolicitarResetSenhaView(APIView):
    serializer_class = SolicitacaoResetSenhaSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = SolicitacaoResetSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = Usuario.objects.filter(
            email__iexact=serializer.validated_data["email"], ativo=True
        ).first()

        if usuario:
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token = default_token_generator.make_token(usuario)
            send_mail(
                "Redefinição de senha ImobiPro",
                f"Use este código para redefinir sua senha:\nuid={uid}\ntoken={token}",
                None,
                [usuario.email],
                fail_silently=True,
            )

        # Resposta idêntica exista ou não o e-mail: não enumeramos usuários.
        return Response(status=status.HTTP_202_ACCEPTED)


@extend_schema(
    request=ConfirmacaoResetSenhaSerializer,
    responses={204: OpenApiResponse(description="Senha redefinida")},
)
class ConfirmarResetSenhaView(APIView):
    serializer_class = ConfirmacaoResetSenhaSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = ConfirmacaoResetSenhaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            pk = force_str(urlsafe_base64_decode(dados["uid"]))
            usuario = Usuario.objects.get(pk=pk)
        except (Usuario.DoesNotExist, ValueError, TypeError):
            usuario = None

        if usuario is None or not default_token_generator.check_token(
            usuario, dados["token"]
        ):
            return Response(
                {
                    "detail": "Link inválido ou expirado.",
                    "code": "token_invalido",
                    "campos": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(dados["nova_senha"])
        usuario.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Equipe da imobiliária. Isolamento por tenant vem do mixin."""

    queryset = Usuario.objects.select_related("tenant").all()
    permission_classes = [IsAuthenticated, PodeGerenciarUsuarios]
    search_fields = ["nome_completo", "email", "creci"]
    filterset_fields = ["papel", "ativo"]
    ordering_fields = ["nome_completo", "criado_em"]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCriacaoSerializer
        return UsuarioSerializer


class IdentidadePublicaView(APIView):
    """GET /api/v1/public/<subdominio>/identidade/ → marca da imobiliária.

    O site público é o mesmo código para todas as imobiliárias; o que muda é a
    marca. Sem esta chamada a vitrine sai na cor padrão do produto, e o cliente
    final vê o site de outra empresa com a cara do ImobiPro.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = IdentidadePublicaSerializer

    @extend_schema(responses=IdentidadePublicaSerializer)
    def get(self, request, subdominio):
        try:
            tenant = Tenant.objects.get(subdominio=subdominio, ativo=True)
        except Tenant.DoesNotExist:
            return Response(
                {"detail": "Site não encontrado."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            IdentidadePublicaSerializer(tenant, context={"request": request}).data
        )
