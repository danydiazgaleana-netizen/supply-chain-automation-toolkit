"""
Casos migrados de los scripts manuales de la sesión de login: hashing,
duplicados, mensaje anti-enumeración, y protección anti auto-lockout.
"""
from core.services.auth_service import (
    AuthService, AuthenticationError, UserAlreadyExistsError, SelfLockoutError,
)
from core.models.entities import UserRole


def test_password_nunca_se_guarda_en_texto_plano(seeded_channels):
    with seeded_channels() as db:
        user = AuthService(db).create_user("u1", "PasswordSegura1", "Usuario Uno", UserRole.OPERADOR)
        assert user.password_hash != "PasswordSegura1"
        assert user.password_hash.startswith("$2b$")  # prefijo bcrypt


def test_password_corto_se_rechaza(seeded_channels):
    with seeded_channels() as db:
        auth = AuthService(db)
        try:
            auth.create_user("u2", "1234", "Usuario Corto", UserRole.OPERADOR)
            assert False, "Debió rechazar password de menos de 8 caracteres"
        except ValueError:
            pass


def test_usuario_duplicado_se_rechaza(seeded_channels):
    with seeded_channels() as db:
        auth = AuthService(db)
        auth.create_user("dup", "PasswordSegura1", "Usuario", UserRole.OPERADOR)
        try:
            auth.create_user("dup", "OtraPassword1", "Otro Usuario", UserRole.OPERADOR)
            assert False, "Debió rechazar username duplicado"
        except UserAlreadyExistsError:
            pass


def test_login_correcto(seeded_channels):
    with seeded_channels() as db:
        AuthService(db).create_user("loginok", "PasswordSegura1", "Usuario", UserRole.OPERADOR)
    with seeded_channels() as db:
        user = AuthService(db).authenticate("loginok", "PasswordSegura1")
        assert user.username == "loginok"


def test_mensaje_identico_para_usuario_inexistente_y_password_incorrecto(seeded_channels):
    """
    Anti-enumeración: el atacante no debe poder distinguir 'usuario no existe'
    de 'password incorrecto' por el mensaje de error.
    """
    with seeded_channels() as db:
        AuthService(db).create_user("real_user", "PasswordSegura1", "Usuario", UserRole.OPERADOR)

    with seeded_channels() as db:
        auth = AuthService(db)
        msg_password_malo = None
        msg_usuario_inexistente = None
        try:
            auth.authenticate("real_user", "PasswordMala1")
        except AuthenticationError as e:
            msg_password_malo = str(e)
        try:
            auth.authenticate("no_existe_para_nada", "cualquiera")
        except AuthenticationError as e:
            msg_usuario_inexistente = str(e)

        assert msg_password_malo == msg_usuario_inexistente
        assert msg_password_malo is not None


def test_admin_no_puede_desactivarse_a_si_mismo(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        auth = AuthService(db)
        try:
            auth.set_active(admin_id, False, acting_admin_id=admin_id)
            assert False, "Debió bloquear auto-desactivación"
        except SelfLockoutError:
            pass


def test_admin_no_puede_quitarse_su_propio_rol(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    with seeded_channels() as db:
        auth = AuthService(db)
        try:
            auth.change_role(admin_id, UserRole.OPERADOR, acting_admin_id=admin_id)
            assert False, "Debió bloquear auto-degradación de rol"
        except SelfLockoutError:
            pass


def test_admin_si_puede_desactivar_a_otro_usuario(admin_and_operator, seeded_channels):
    admin_id = admin_and_operator["admin_id"]
    operator_id = admin_and_operator["operator_id"]
    with seeded_channels() as db:
        auth = AuthService(db)
        user = auth.set_active(operator_id, False, acting_admin_id=admin_id)
        assert user.is_active is False
