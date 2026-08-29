from datetime import datetime, timezone

from ai_engine import rate_limit as RL


class FakeSnapshot:
    def __init__(
        self,
        data=None,
    ):
        self._data = dict(
            data
            or {}
        )

        self.exists = bool(
            data is not None
        )

    def to_dict(
        self,
    ):
        return dict(
            self._data
        )


class FakeRef:
    def __init__(
        self,
        db,
        collection,
        document,
    ):
        self.db = db
        self.collection_name = collection
        self.document_name = document

    @property
    def key(
        self,
    ):
        return (
            self.collection_name,
            self.document_name,
        )

    def get(
        self,
        transaction=None,
    ):
        data = self.db.data.get(
            self.key
        )

        return FakeSnapshot(
            data
        )


class FakeCollection:
    def __init__(
        self,
        db,
        name,
    ):
        self.db = db
        self.name = name

    def document(
        self,
        name,
    ):
        return FakeRef(
            self.db,
            self.name,
            name,
        )


class FakeTransaction:
    def __init__(
        self,
        db,
    ):
        self.db = db

    def set(
        self,
        ref,
        payload,
        merge=False,
    ):
        current = dict(
            self.db.data.get(
                ref.key,
                {},
            )
        )

        if merge:
            current.update(
                payload
            )
        else:
            current = dict(
                payload
            )

        self.db.data[
            ref.key
        ] = current


class FakeDb:
    def __init__(
        self,
    ):
        self.data = {}

    def collection(
        self,
        name,
    ):
        return FakeCollection(
            self,
            name,
        )

    def transaction(
        self,
    ):
        return FakeTransaction(
            self
        )


def make_transactional_direct(
    monkeypatch,
):
    monkeypatch.setattr(
        RL.firestore,
        "transactional",
        lambda fn: fn,
    )


def freeze_time(
    monkeypatch,
):
    now = datetime(
        2026,
        8,
        28,
        22,
        30,
        10,
        tzinfo=timezone.utc,
    )

    monkeypatch.setattr(
        RL,
        "_now",
        lambda: now,
    )

    return now


def test_image_creation_guard_consumes_user_and_platform(
    monkeypatch,
):
    make_transactional_direct(
        monkeypatch
    )

    now = freeze_time(
        monkeypatch
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_MINUTE",
        4,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_HOUR",
        30,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_DAY",
        100,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PLATFORM_PER_DAY",
        5000,
    )

    db = FakeDb()

    result = (
        RL.check_and_consume_image_creation(
            db,
            "user-a",
        )
    )

    assert result == {
        "allowed": True,
        "reason": None,
        "retryAfter": 0,
    }

    mk, hk, dk = RL._keys(
        now
    )

    user = db.data[
        (
            "aiRateLimits",
            "image_user-a",
        )
    ]

    platform = db.data[
        (
            "aiRateLimits",
            "image_platform_daily",
        )
    ]

    assert user["minKey"] == mk
    assert user["hourKey"] == hk
    assert user["dayKey"] == dk
    assert user["minCount"] == 1
    assert user["hourCount"] == 1
    assert user["dayCount"] == 1
    assert (
        user["kind"]
        == "ai_image_creation"
    )

    assert platform["dayKey"] == dk
    assert platform["dayCount"] == 1


def test_image_creation_minute_denial_does_not_increment(
    monkeypatch,
):
    make_transactional_direct(
        monkeypatch
    )

    now = freeze_time(
        monkeypatch
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_MINUTE",
        1,
    )

    db = FakeDb()

    mk, hk, dk = RL._keys(
        now
    )

    db.data[
        (
            "aiRateLimits",
            "image_user-a",
        )
    ] = {
        "minKey": mk,
        "minCount": 1,
        "hourKey": hk,
        "hourCount": 1,
        "dayKey": dk,
        "dayCount": 1,
    }

    before = dict(
        db.data[
            (
                "aiRateLimits",
                "image_user-a",
            )
        ]
    )

    result = (
        RL.check_and_consume_image_creation(
            db,
            "user-a",
        )
    )

    assert result["allowed"] is False
    assert result["reason"] == "minute"
    assert result["retryAfter"] > 0

    assert (
        db.data[
            (
                "aiRateLimits",
                "image_user-a",
            )
        ]
        == before
    )

    assert (
        (
            "aiRateLimits",
            "image_platform_daily",
        )
        not in db.data
    )


def test_platform_cap_denies_without_user_increment(
    monkeypatch,
):
    make_transactional_direct(
        monkeypatch
    )

    now = freeze_time(
        monkeypatch
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_MINUTE",
        100,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_HOUR",
        100,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PER_DAY",
        100,
    )

    monkeypatch.setattr(
        RL,
        "IMAGE_CREATE_PLATFORM_PER_DAY",
        1,
    )

    db = FakeDb()

    _, _, dk = RL._keys(
        now
    )

    db.data[
        (
            "aiRateLimits",
            "image_platform_daily",
        )
    ] = {
        "dayKey": dk,
        "dayCount": 1,
    }

    result = (
        RL.check_and_consume_image_creation(
            db,
            "user-a",
        )
    )

    assert result["allowed"] is False
    assert result["reason"] == "platform"

    assert (
        (
            "aiRateLimits",
            "image_user-a",
        )
        not in db.data
    )


def test_guard_invalid_user_fails_closed():
    db = FakeDb()

    result = (
        RL.check_and_consume_image_creation(
            db,
            "",
        )
    )

    assert result == {
        "allowed": False,
        "reason": "invalid_user",
        "retryAfter": 0,
    }


def test_guard_store_failure_fails_closed():
    class BrokenDb:
        def collection(
            self,
            _name,
        ):
            raise RuntimeError(
                "firestore unavailable"
            )

    result = (
        RL.check_and_consume_image_creation(
            BrokenDb(),
            "user-a",
        )
    )

    assert result["allowed"] is False

    assert (
        result["reason"]
        == "guard_unavailable"
    )

    assert result["retryAfter"] == 30
