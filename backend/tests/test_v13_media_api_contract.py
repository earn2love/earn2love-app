from pathlib import Path
import ast


SERVER = Path(
    "backend/server.py"
)


def source():
    return SERVER.read_text(
        encoding="utf-8-sig"
    )


def test_upload_route_exists():
    value = source()

    assert (
        '@api.post("/ai/media/upload")'
        in value
    )


def test_upload_route_requires_verified_user_dependency():
    value = source()

    section = value.split(
        '@api.post("/ai/media/upload")',
        1,
    )[1].split(
        '@api.delete("/ai/media/{image_id}")',
        1,
    )[0]

    assert (
        "Depends(get_current_user)"
        in section
    )

    assert (
        'user_id=user["uid"]'
        in section
    )


def test_upload_never_accepts_uid_form_field():
    tree = ast.parse(
        source()
    )

    target = None

    for node in ast.walk(
        tree
    ):
        if (
            isinstance(
                node,
                (
                    ast.AsyncFunctionDef,
                    ast.FunctionDef,
                ),
            )
            and node.name
            == "ai_media_upload"
        ):
            target = node
            break

    assert target is not None

    params = {
        arg.arg
        for arg
        in (
            target.args.args
            + target.args.kwonlyargs
        )
    }

    assert "uid" not in params
    assert "userId" not in params
    assert "user_id" not in params


def test_delete_route_requires_verified_user():
    value = source()

    section = value.split(
        '@api.delete("/ai/media/{image_id}")',
        1,
    )[1].split(
        "# ---------------- Advanced AI Character Engine",
        1,
    )[0]

    assert (
        "Depends(get_current_user)"
        in section
    )

    assert (
        'user_id=user["uid"]'
        in section
    )


def test_v13_routes_do_not_create_public_url():
    value = source()

    section = value.split(
        "# ---- V13 authenticated temporary image media ----",
        1,
    )[1].split(
        "# ---------------- Advanced AI Character Engine",
        1,
    )[0]

    forbidden = [
        "make_public(",
        "public_url",
        "acl",
        "allUsers",
    ]

    for marker in forbidden:
        assert marker not in section
