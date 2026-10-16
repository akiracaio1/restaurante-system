import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from rbac_db import enter_operacao_role
import models

logger = logging.getLogger("restaurante.auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_INSECURE_FALLBACK = "fallback-insecure-key"
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == _INSECURE_FALLBACK:
    # O repositório é público: uma chave padrão permitiria forjar tokens Master.
    # Sem variável configurada, usa uma chave aleatória por processo (os logins
    # caem a cada reinício até JWT_SECRET_KEY ser definida no servidor).
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("JWT_SECRET_KEY não definida: usando chave aleatória temporária. Defina-a no servidor.")
ALGORITHM = "HS256"
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_authenticated_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    """Usuário autenticado de QUALQUER perfil.

    O perfil e o status vêm sempre do banco, nunca do token: rebaixar ou
    desativar alguém vale na próxima requisição.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise exc

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.role not in models.ROLES:
        raise exc
    if user.account_id is None:
        user.account_id = user.id
    return user


async def get_current_user(user: models.User = Depends(get_authenticated_user)) -> models.User:
    """Somente Master. É o padrão de todas as rotas: perfil Operação recebe 403.

    Uma rota só fica aberta à Operação se declarar explicitamente
    `get_operational_context`.
    """
    if user.role != models.ROLE_MASTER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso restrito ao perfil Master")
    return user


@dataclass
class OperationalContext:
    db: AsyncSession
    user: models.User

    @property
    def is_master(self) -> bool:
        return self.user.role == models.ROLE_MASTER

    @property
    def account_id(self) -> int:
        return self.user.account_id


async def get_operational_context(
    user: models.User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> OperationalContext:
    """Rotas de leitura abertas aos dois perfis.

    Para Operação, a sessão passa a rodar sob o papel restrito do banco.
    """
    if user.role == models.ROLE_OPERACAO:
        await enter_operacao_role(db, user.account_id)
    return OperationalContext(db=db, user=user)
