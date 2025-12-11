import json
import logging
from functools import lru_cache
from typing import List, Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config.config import ENV_VARIABLES

logger = logging.getLogger(__name__)


class AzureADSettings:
    """
    Configuración básica para validar tokens de Azure Entra ID (Azure AD).
    Los valores se leen de variables de entorno definidas en .env o el sistema.
    """

    def __init__(self) -> None:
        tenant_id = ENV_VARIABLES.get("AZURE_AD_TENANT_ID")
        client_id = ENV_VARIABLES.get("AZURE_AD_CLIENT_ID")

        if not tenant_id or not client_id:
            raise RuntimeError(
                "AZURE_AD_TENANT_ID y AZURE_AD_CLIENT_ID deben estar configurados en el entorno"
            )

        self.tenant_id: str = tenant_id
        self.client_id: str = client_id

        # Emisor esperado del token (issuer)
        # Para tenants comunes podrías usar 'organizations' o 'common'
        self.issuer: str = ENV_VARIABLES.get(
            "AZURE_AD_ISSUER",
            f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        )

        # URL de configuración OpenID y JWKS
        self.openid_config_url: str = ENV_VARIABLES.get(
            "AZURE_AD_OPENID_CONFIG_URL",
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
        )
        self.jwks_uri: Optional[str] = ENV_VARIABLES.get("AZURE_AD_JWKS_URI")

        # Audiencia esperada (API / Application ID URI); por defecto el client_id
        self.audience: str = ENV_VARIABLES.get("AZURE_AD_AUDIENCE", client_id)


@lru_cache()
def get_settings() -> AzureADSettings:
    return AzureADSettings()


@lru_cache()
def get_openid_config(settings: AzureADSettings) -> dict:
    """
    Descarga y cachea el documento de configuración OpenID de Entra ID.
    """
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(settings.openid_config_url)
        resp.raise_for_status()
        return resp.json()


@lru_cache()
def get_jwks(settings: AzureADSettings) -> dict:
    """
    Descarga y cachea las claves públicas (JWKS) de Entra ID.
    """
    jwks_uri = settings.jwks_uri
    if not jwks_uri:
        config = get_openid_config(settings)
        jwks_uri = config.get("jwks_uri")
        if not jwks_uri:
            raise RuntimeError("No se pudo obtener jwks_uri desde la configuración OpenID")

    with httpx.Client(timeout=5.0) as client:
        resp = client.get(jwks_uri)
        resp.raise_for_status()
        return resp.json()


def _get_signing_key(token: str, jwks: dict) -> dict:
    """
    Busca en el JWKS la clave correspondiente al 'kid' del header del token.
    """
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin 'kid' en el encabezado",
        )

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se encontró clave de firma para el token",
    )


def _build_public_key(jwk_data: dict):
    """
    Construye la clave pública a partir de los datos JWK de Azure.
    La librería jose puede aceptar directamente el dict JWK como 'key'.
    """
    return jwk.construct(jwk_data, algorithm="RS256")


def validate_jwt(token: str, settings: AzureADSettings) -> dict:
    """
    Valida el token JWT emitido por Azure Entra ID y devuelve sus claims.
    """
    jwks = get_jwks(settings)
    signing_jwk = _get_signing_key(token, jwks)

    # Log de configuración para debug
    logger.info(f"Validando token - Audience esperada: {settings.audience}")
    logger.info(f"Validando token - Issuer esperado: {settings.issuer}")
    
    # Decodificar sin validar para ver los claims del token
    try:
        unverified_claims = jwt.get_unverified_claims(token)
        logger.info(f"Token aud claim: {unverified_claims.get('aud')}")
        logger.info(f"Token iss claim: {unverified_claims.get('iss')}")
        logger.info(f"Token ver claim: {unverified_claims.get('ver')}")
        logger.info(f"Token scp claim: {unverified_claims.get('scp')}")
    except Exception as e:
        logger.warning(f"No se pudieron leer claims sin verificar: {e}")

    # Azure puede emitir access tokens con issuer v1 (sts.windows.net) o v2 (login.microsoftonline.com/.../v2.0)
    # y el audience puede ser el App ID URI (api://...) o el Client ID puro, dependiendo de la configuración y versión.
    allowed_issuers = [
        settings.issuer,  # v2 por defecto
        f"https://sts.windows.net/{settings.tenant_id}/",  # v1
    ]
    
    allowed_audiences = [
        settings.audience,  # Configurado en ENV (usualmente api://...)
        settings.client_id, # Client ID puro
    ]

    last_error: Exception | None = None
    
    # Probar combinaciones válidas de issuer y audience
    for aud in allowed_audiences:
        for iss in allowed_issuers:
            try:
                claims = jwt.decode(
                    token,
                    signing_jwk,
                    algorithms=["RS256"],
                    audience=aud,
                    issuer=iss,
                )
                logger.info(f"Token validado exitosamente. Aud: {aud}, Iss: {iss}")
                return claims
            except JWTError as e:
                # Si el error es expiración, es crítico y deberíamos reportarlo tal cual si fuera la config correcta.
                # Pero en este loop probamos configuraciones, así que guardamos el último error.
                last_error = e

    logger.error(f"Error validando token JWT (todas las combinaciones fallaron): {str(last_error)}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Token inválido: {str(last_error)}",
    ) from last_error


def _extract_email_from_claims(claims: dict) -> Optional[str]:
    """
    Intenta obtener el correo del usuario desde distintos claims habituales.
    """
    # En tokens de Entra ID suele venir en 'preferred_username' o 'upn' o 'email'
    for key in ("preferred_username", "upn", "email"):
        value = claims.get(key)
        if value:
            return value

    # A veces viene como lista en 'emails'
    emails = claims.get("emails")
    if isinstance(emails, list) and emails:
        return emails[0]

    return None


def _extract_groups_from_claims(claims: dict) -> List[str]:
    """
    Extrae los grupos (por defecto IDs de grupo) del token.
    Nota: Para que el claim 'groups' exista, debes configurarlo en la app de Entra ID.
    """
    groups = claims.get("groups") or []
    if isinstance(groups, list):
        return [str(g) for g in groups]
    return []


async def get_current_user_claims(
    request: Request, settings: AzureADSettings = Depends(get_settings)
) -> dict:
    """
    Dependencia de FastAPI que:
    - Lee el header Authorization: Bearer <token>
    - Valida el token con Azure Entra ID
    - Devuelve los claims del usuario
    """
    logger.info("=== Iniciando validación de token ===")
    
    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        logger.warning("Petición sin header Authorization válido")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta encabezado Authorization con Bearer token",
        )

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        logger.warning("Token Bearer vacío")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer vacío",
        )

    logger.info(f"Token recibido (primeros 50 chars): {token[:50]}...")
    claims = validate_jwt(token, settings)
    return claims


def build_user_info_from_claims(claims: dict) -> dict:
    """
    Construye un dict con la información básica de usuario a partir de los claims.
    """
    email = _extract_email_from_claims(claims)
    groups = _extract_groups_from_claims(claims)

    return {
        "id": claims.get("oid") or claims.get("sub"),
        "name": claims.get("name"),
        "email": email,
        "groups": groups,
        "raw_claims": claims,
    }


