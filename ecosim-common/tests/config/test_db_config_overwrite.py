from ecosim_common.config.db_config_overwrite import DbConfigOverwrite


def test_ssl_false_overrides_a_default_of_true() -> None:
    assert DbConfigOverwrite(_ssl=False).ssl(default=True) is False


def test_ssl_true_overrides_a_default_of_false() -> None:
    assert DbConfigOverwrite(_ssl=True).ssl(default=False) is True


def test_ssl_falls_back_to_the_default_if_it_is_not_set() -> None:
    assert DbConfigOverwrite().ssl(default=True) is True
    assert DbConfigOverwrite().ssl(default=False) is False


def test_the_representation_does_not_show_the_password() -> None:
    assert "hunter7" not in repr(DbConfigOverwrite(_user_password="hunter7"))
