"""
Direct tests: drive the contract's public methods against a fake runtime
(web, model and clock are mocked). They check registration, challenges,
staleness, cooldowns, access control and bounded history. They do not
simulate validator agreement.
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fake_genlayer import load_contract  # noqa: E402

gl, C = load_contract()

OWNER, OTHER = "aa", "bb"
HOST = "raw.githubusercontent.com"
URL = f"https://{HOST}/acme/api/main/docs/limits.md"
T0 = 1_800_000_000
DAY = 86400


def sha(b):
    return hashlib.sha256(b).hexdigest()


def publish(value, unit="minute", extra=""):
    """Put a docs page online and make the (mocked) model read it correctly."""
    sentence = f"The API rate limit is {value} requests per {unit}."
    body = f"# Limits\n\n{sentence}\n{extra}\n".encode()
    gl.web.pages[URL] = (200, body)
    gl.llm_answer = json.dumps({"value": str(value), "unit": unit, "quote": sentence})
    return sha(body)


class Base(unittest.TestCase):
    def setUp(self):
        gl.set_time(T0)
        gl.web.pages.clear()
        gl.llm_calls = 0
        gl.as_user(OWNER)
        self.c = C.DocsClaimLedger()
        self.c.create_ledger("acme-docs", HOST)

    def register(self, value=100, cid="rate-limit", cmp="<=", max_age=7 * DAY, **over):
        h = publish(value)
        args = dict(ledger_id="acme-docs", claim_id=cid, docs_url=URL, docs_sha256=h,
                    topic="default API rate limit", kind="rate", comparator=cmp,
                    expected=100, expected_unit="minute", anchors="rate,limit",
                    max_age_seconds=max_age)
        args.update(over)
        gl.as_user(OWNER)
        return self.c.register_claim(**args), h

    def claim(self, cid="rate-limit"):
        return self.c.get_claim("acme-docs", cid)


class RegistrationTests(Base):
    def test_registers_when_baseline_holds(self):
        out, h = self.register()
        c = self.claim()
        self.assertEqual(out, "VERIFIED")
        self.assertEqual((c["status"], c["baseline_sha256"], c["baseline"]), ("VERIFIED", h, {"value": 100, "unit": "minute"}))
        self.assertEqual(c["fresh_until"], T0 + 7 * DAY)

    def test_rejects_claim_that_does_not_hold_at_registration(self):
        with self.assertRaises(gl.vm.UserError):
            self.register(value=500)
        with self.assertRaises(gl.vm.UserError):
            self.c.get_claim("acme-docs", "rate-limit")

    def test_wrong_hash_rejected(self):
        with self.assertRaises(gl.vm.UserError):
            self.register(docs_sha256="0" * 64)

    def test_only_owner_registers(self):
        publish(100)
        gl.as_user(OTHER)
        with self.assertRaises(gl.vm.UserError):
            self.c.register_claim("acme-docs", "x-claim", URL, sha(gl.web.pages[URL][1]), "default API rate limit",
                                  "rate", "<=", 100, "minute", "rate,limit", 7 * DAY)

    def test_host_must_match_ledger(self):
        with self.assertRaises(gl.vm.UserError):
            self.register(docs_url="https://evil.example/limits.md")

    def test_input_validation(self):
        bad = [dict(kind="size"), dict(comparator="<"), dict(expected=-1), dict(expected_unit="parsec"),
               dict(anchors=""), dict(anchors="a,b,c,d"), dict(topic="x"), dict(topic="bad <tag> topic"),
               dict(max_age=60), dict(max_age=400 * DAY), dict(cid="Bad Id!")]
        for i, over in enumerate(bad):
            with self.assertRaises(gl.vm.UserError, msg=str(over)):
                self.register(**over)

    def test_count_kind_requires_empty_unit(self):
        with self.assertRaises(gl.vm.UserError):
            self.register(kind="count", expected_unit="minute")

    def test_duplicate_and_cap(self):
        self.register()
        with self.assertRaises(gl.vm.UserError):
            self.register()
        for i in range(C.MAX_LEDGER_CLAIMS - 1):
            self.register(cid=f"claim-{i:03d}")
        with self.assertRaises(gl.vm.UserError):
            self.register(cid="one-too-many")


class ChallengeTests(Base):
    def test_contradiction_changes_status_and_records_evidence(self):
        self.register()
        gl.set_time(T0 + 1000)
        h2 = publish(200)
        gl.as_user(OTHER)
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", h2), "CONTRADICTED")
        c = self.claim()
        self.assertEqual(c["status"], "CONTRADICTED")
        self.assertEqual(c["contradicting"], {"value": 200, "unit": "minute"})
        self.assertEqual(c["contradicted_by"], "0x" + OTHER * 20)
        self.assertEqual(c["history"][-1]["outcome"], "CONTRADICTED")

    def test_anyone_can_challenge_not_only_owner_or_members(self):
        self.register()
        gl.set_time(T0 + 1000)
        h2 = publish(100, extra="Updated wording.")
        gl.as_user("cc")
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", h2), "RECONFIRMED")

    def test_reconfirm_refreshes_freshness(self):
        self.register()
        gl.set_time(T0 + 1000)
        h2 = publish(100, extra="Changed.")
        self.c.challenge("acme-docs", "rate-limit", h2)
        c = self.claim()
        self.assertEqual((c["status"], c["reconfirmed"], c["last_verified_at"]), ("VERIFIED", 1, T0 + 1000))
        self.assertEqual(c["fresh_until"], T0 + 1000 + 7 * DAY)

    def test_same_docs_cannot_be_resampled(self):
        _, h = self.register()
        gl.set_time(T0 + 1000)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", h)

    def test_stale_claim_can_be_reconfirmed_on_unchanged_docs(self):
        _, h = self.register(max_age=DAY)
        gl.set_time(T0 + DAY + 10)
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", h), "RECONFIRMED")
        self.assertEqual(self.claim()["last_verified_at"], T0 + DAY + 10)
        gl.set_time(T0 + DAY + 10 + C.CHALLENGE_COOLDOWN + 1)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", h)

    def test_cooldown(self):
        self.register()
        gl.set_time(T0 + 1000)
        self.c.challenge("acme-docs", "rate-limit", publish(100, extra="a"))
        gl.set_time(T0 + 1100)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", publish(100, extra="b"))
        gl.set_time(T0 + 1000 + C.CHALLENGE_COOLDOWN)
        self.c.challenge("acme-docs", "rate-limit", publish(100, extra="b"))

    def test_inconclusive_changes_nothing_but_is_recorded(self):
        self.register()
        gl.set_time(T0 + 1000)
        h2 = publish(100, extra="x")
        gl.llm_answer = json.dumps({"value": "100", "unit": "minute", "quote": "The API rate limit is a made-up sentence."})
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", h2), "INCONCLUSIVE")
        c = self.claim()
        self.assertEqual((c["status"], c["reconfirmed"]), ("VERIFIED", 0))
        self.assertEqual(c["history"][-1]["reason"], "llm_quote_not_in_docs")
        self.assertNotIn(h2, c["assessed"])

    def test_wrong_commitment_is_inconclusive_not_trusted(self):
        self.register()
        gl.set_time(T0 + 1000)
        publish(200)
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", "1" * 64), "INCONCLUSIVE")
        self.assertEqual(self.claim()["status"], "VERIFIED")
        self.assertEqual(self.claim()["history"][-1]["reason"], "docs_hash_mismatch")

    def test_docs_removed_is_inconclusive(self):
        self.register()
        gl.set_time(T0 + 1000)
        gl.web.pages[URL] = (404, b"")
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", "2" * 64), "INCONCLUSIVE")
        self.assertEqual(self.claim()["history"][-1]["reason"], "docs_http_404")

    def test_cannot_challenge_a_settled_claim(self):
        self.register()
        gl.set_time(T0 + 1000)
        self.c.challenge("acme-docs", "rate-limit", publish(200))
        gl.set_time(T0 + 5000)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", publish(100, extra="again"))

    def test_history_is_bounded_and_challenges_capped(self):
        self.register(max_age=365 * DAY)
        t = T0
        for i in range(C.MAX_CHALLENGES_PER_CLAIM):
            t += C.CHALLENGE_COOLDOWN
            gl.set_time(t)
            self.c.challenge("acme-docs", "rate-limit", publish(100, extra=f"v{i}"))
        c = self.claim()
        self.assertEqual(len(c["history"]), C.HISTORY_LIMIT)
        self.assertEqual(c["challenge_count"], C.MAX_CHALLENGES_PER_CLAIM)
        gl.set_time(t + C.CHALLENGE_COOLDOWN)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", publish(100, extra="over"))

    def test_unit_change_is_judged_by_rate_not_by_number(self):
        # "<= 100 per minute": 100 per day is slower, so the claim still holds.
        self.register()
        gl.set_time(T0 + 1000)
        self.assertEqual(self.c.challenge("acme-docs", "rate-limit", publish(100, unit="day")), "RECONFIRMED")
        # ">= 100 per minute": the same docs now contradict the claim.
        self.register(cid="min-rate", cmp=">=")
        gl.set_time(T0 + 5000)
        self.assertEqual(self.c.challenge("acme-docs", "min-rate", publish(100, unit="day", extra="z")), "CONTRADICTED")

    def test_equality_claim_flags_any_change(self):
        self.register(cid="exact-limit", cmp="==")
        gl.set_time(T0 + 1000)
        self.assertEqual(self.c.challenge("acme-docs", "exact-limit", publish(60)), "CONTRADICTED")


class RetireAndAuditTests(Base):
    def test_only_owner_retires(self):
        self.register()
        gl.as_user(OTHER)
        with self.assertRaises(gl.vm.UserError):
            self.c.retire_claim("acme-docs", "rate-limit")
        gl.as_user(OWNER)
        self.c.retire_claim("acme-docs", "rate-limit")
        self.assertEqual(self.claim()["status"], "RETIRED")
        with self.assertRaises(gl.vm.UserError):
            self.c.retire_claim("acme-docs", "rate-limit")

    def test_retired_claim_not_challengeable(self):
        self.register()
        self.c.retire_claim("acme-docs", "rate-limit")
        gl.set_time(T0 + 1000)
        with self.assertRaises(gl.vm.UserError):
            self.c.challenge("acme-docs", "rate-limit", publish(200))

    def test_event_log(self):
        self.register()
        gl.set_time(T0 + 1000)
        self.c.challenge("acme-docs", "rate-limit", publish(200))
        kinds = [self.c.get_event(i)["kind"] for i in range(self.c.event_count())]
        self.assertEqual(kinds, ["LEDGER_CREATED", "CLAIM_REGISTERED", "CHALLENGE_CONTRADICTED"])

    def test_ledger_isolation(self):
        self.register()
        self.c.create_ledger("other-docs", HOST)
        with self.assertRaises(gl.vm.UserError):
            self.c.get_claim("other-docs", "rate-limit")

    def test_ledger_validation(self):
        with self.assertRaises(gl.vm.UserError):
            self.c.create_ledger("Bad Id", HOST)
        with self.assertRaises(gl.vm.UserError):
            self.c.create_ledger("acme-docs", HOST)
        with self.assertRaises(gl.vm.UserError):
            self.c.create_ledger("new-ledger", "Bad Host!")


if __name__ == "__main__":
    unittest.main()
