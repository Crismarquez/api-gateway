from fastapi import APIRouter, Depends

from app.auth.azure_ad import build_user_info_from_claims, get_current_user_claims


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def read_current_user(claims: dict = Depends(get_current_user_claims)):
    """
    Endpoint que valida el token de Azure Entra ID enviado en el header Authorization
    y devuelve información básica del usuario junto con los grupos.

    Debes enviar el token de acceso/id token obtenido en el frontend con:

        Authorization: Bearer <token>
    """
    user_info = build_user_info_from_claims(claims)
    return {
        "user": {
            "id": user_info["id"],
            "name": user_info["name"],
            "email": user_info["email"],
            "groups": user_info["groups"],
        }
    }


