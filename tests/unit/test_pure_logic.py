import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fake_genlayer import load_contract  # noqa: E402

gl, C = load_contract()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def inp(docs, kind="rate", cmp="<=", expected=100, unit="minute", anchors=("rate", "limit")):
    return {"kind": kind, "comparator": cmp, "expected": expected, "expected_unit": unit,
            "topic": "default API rate limit", "anchors": list(anchors), "docs_sha256": sha(docs)}


def answer(value="100", unit="minute", quote="The API rate limit is 100 requests per minute."):
    return json.dumps({"value": value, "unit": unit, "quote": quote})


DOCS = b"# Limits\n\nThe API rate limit is 100 requests per minute.\n\nOther text here.\n"


def no_llm(*a):
    raise AssertionError("llm must not be called")


class SatisfiesTests(unittest.TestCase):
    def test_count(self):
        self.assertTrue(C.satisfies("count", "==", 50, "", 50, ""))
        self.assertFalse(C.satisfies("count", "==", 51, "", 50, ""))
        self.assertTrue(C.satisfies("count", "<=", 49, "", 50, ""))
        self.assertTrue(C.satisfies("count", ">=", 50, "", 50, ""))
        self.assertFalse(C.satisfies("count", ">=", 49, "", 50, ""))

    def test_duration_converts_units(self):
        self.assertTrue(C.satisfies("duration", "==", 60, "second", 1, "minute"))
        self.assertTrue(C.satisfies("duration", "==", 2, "hour", 120, "minute"))
        self.assertTrue(C.satisfies("duration", "<=", 23, "hour", 1, "day"))
        self.assertFalse(C.satisfies("duration", "<=", 25, "hour", 1, "day"))

    def test_rate_converts_periods(self):
        self.assertTrue(C.satisfies("rate", "==", 60, "minute", 1, "second"))
        self.assertFalse(C.satisfies("rate", "==", 61, "minute", 1, "second"))
        self.assertTrue(C.satisfies("rate", "==", 60, "minute", 3600, "hour"))
        self.assertTrue(C.satisfies("rate", "<=", 1, "second", 100, "minute"))
        self.assertFalse(C.satisfies("rate", "<=", 2, "second", 100, "minute"))
        self.assertTrue(C.satisfies("rate", ">=", 6000, "hour", 100, "minute"))

    def test_rate_period_direction_is_not_swapped(self):
        # 100 per day is far slower than 100 per minute
        self.assertTrue(C.satisfies("rate", "<=", 100, "day", 100, "minute"))
        self.assertFalse(C.satisfies("rate", ">=", 100, "day", 100, "minute"))


class AnchorTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(C.parse_anchors("Rate, limit"), ["rate", "limit"])

    def test_invalid(self):
        for bad in ["", "a", "rate,rate", "a,b,c,d", "bad word", "x" * 21 + ",rate"]:
            with self.assertRaises(ValueError, msg=bad):
                C.parse_anchors(bad)


class NumberTests(unittest.TestCase):
    def test_whole_numbers_only(self):
        self.assertTrue(C.number_in_quote(100, "limit is 100 per minute"))
        self.assertTrue(C.number_in_quote(1000, "limit is 1,000 per minute"))
        self.assertTrue(C.number_in_quote(100, "limit is 100."))
        self.assertFalse(C.number_in_quote(100, "limit is 1000 per minute"))
        self.assertFalse(C.number_in_quote(100, "limit is 100.5 per minute"))
        self.assertFalse(C.number_in_quote(100, "limit is 2100 per minute"))
        self.assertFalse(C.number_in_quote(5, "limit is 0.5 per minute"))


class ValidateTests(unittest.TestCase):
    def v(self, raw, docs=DOCS, **kw):
        return C.validate_extraction(raw, docs.decode(), inp(docs, **kw))

    def test_good(self):
        self.assertEqual(self.v(answer()), ({"value": 100, "unit": "minute"}, ""))

    def test_fenced(self):
        self.assertEqual(self.v("```json\n" + answer() + "\n```")[0]["value"], 100)

    def test_commas_in_value(self):
        docs = b"The API rate limit is 1,000 requests per minute.\n"
        r = self.v(answer("1,000", quote="The API rate limit is 1,000 requests per minute."), docs=docs)
        self.assertEqual(r[0]["value"], 1000)

    def test_not_json(self):
        self.assertEqual(self.v("verdict: HOLDS")[1], "llm_not_json")

    def test_null_value(self):
        self.assertEqual(self.v(json.dumps({"value": None, "unit": "minute", "quote": "x"}))[1], "llm_no_value")

    def test_bad_value_shapes(self):
        for bad in ["1.5", "-3", "abc", "1e3", True]:
            raw = json.dumps({"value": bad, "unit": "minute", "quote": "q"})
            self.assertEqual(self.v(raw)[1], "llm_value_invalid", bad)

    def test_bad_unit(self):
        self.assertEqual(self.v(answer(unit="parsec"))[1], "llm_unit_invalid")
        self.assertEqual(self.v(answer(unit=""), )[1], "llm_unit_invalid")

    def test_count_requires_empty_unit(self):
        docs = b"Each page returns at most 50 items for the page size.\n"
        q = "Each page returns at most 50 items for the page size."
        ok = self.v(answer("50", "", q), docs=docs, kind="count", cmp="==", expected=50, unit="", anchors=("page", "size"))
        self.assertEqual(ok[0], {"value": 50, "unit": ""})
        bad = self.v(answer("50", "minute", q), docs=docs, kind="count", cmp="==", expected=50, unit="", anchors=("page", "size"))
        self.assertEqual(bad[1], "llm_unit_invalid")

    def test_fabricated_quote(self):
        self.assertEqual(self.v(answer(quote="The API rate limit is 100 requests per second."))[1], "llm_quote_not_in_docs")

    def test_quote_must_hold_anchors(self):
        docs = b"The API rate limit is 100 requests per minute.\nUnrelated: limit of 7 minutes for sessions.\n"
        self.assertEqual(self.v(answer("7", "minute", "Unrelated: limit of 7 minutes for sessions."), docs=docs)[1], "llm_anchor_not_in_quote")

    def test_value_must_be_in_quote(self):
        self.assertEqual(self.v(answer(value="60"))[1], "llm_value_not_in_quote")

    def test_unit_must_be_in_quote(self):
        self.assertEqual(self.v(answer(unit="hour"))[1], "llm_unit_not_in_quote")

    def test_quote_length(self):
        self.assertEqual(self.v(answer(quote="100"))[1], "llm_quote_length")

    def test_quote_whitespace_tolerated(self):
        docs = b"The API rate limit is\n100 requests per   minute.\n"
        r = self.v(answer(quote="The API rate limit is 100 requests per minute."), docs=docs)
        self.assertEqual(r[0]["value"], 100)

    def test_model_cannot_supply_verdict(self):
        raw = json.dumps({"value": "100", "unit": "minute", "verdict": "CONTRADICTED",
                          "quote": "The API rate limit is 100 requests per minute."})
        rep = C.assess(inp(DOCS), (200, DOCS), lambda t, i: raw)
        self.assertEqual(rep["verdict"], "HOLDS")


class AssessTests(unittest.TestCase):
    def go(self, docs=DOCS, status=200, llm=None, **kw):
        llm = llm or (lambda t, i: answer())
        i = inp(docs, **kw)
        return C.assess(i, (status, docs), llm)

    def test_holds(self):
        r = self.go()
        self.assertEqual((r["verdict"], r["observed"]), ("HOLDS", {"value": 100, "unit": "minute"}))

    def test_contradicted(self):
        docs = b"The API rate limit is 200 requests per minute.\n"
        r = self.go(docs=docs, llm=lambda t, i: answer("200", quote="The API rate limit is 200 requests per minute."))
        self.assertEqual((r["verdict"], r["reason"]), ("CONTRADICTED", "claim_not_satisfied"))

    def test_equality_claim(self):
        docs = b"The API rate limit is 60 requests per minute.\n"
        llm = lambda t, i: answer("60", quote="The API rate limit is 60 requests per minute.")
        self.assertEqual(self.go(docs=docs, llm=llm, cmp="==", expected=100)["verdict"], "CONTRADICTED")
        self.assertEqual(self.go(docs=docs, llm=llm, cmp="==", expected=60)["verdict"], "HOLDS")

    def test_unit_change_is_caught(self):
        docs = b"The API rate limit is 100 requests per day.\n"
        llm = lambda t, i: answer("100", "day", "The API rate limit is 100 requests per day.")
        self.assertEqual(self.go(docs=docs, llm=llm, cmp=">=", expected=100, unit="minute")["verdict"], "CONTRADICTED")

    def test_http_error(self):
        self.assertEqual(self.go(status=404, llm=no_llm)["reason"], "docs_http_404")

    def test_hash_mismatch(self):
        i = inp(DOCS)
        i["docs_sha256"] = "0" * 64
        r = C.assess(i, (200, DOCS), no_llm)
        self.assertEqual((r["verdict"], r["reason"]), ("UNKNOWN", "docs_hash_mismatch"))

    def test_oversize(self):
        big = DOCS + b"#" * C.MAX_BODY_BYTES
        self.assertEqual(self.go(docs=big, llm=no_llm)["reason"], "docs_too_large")

    def test_not_utf8(self):
        self.assertEqual(self.go(docs=b"rate limit \xff\xfe", llm=no_llm)["reason"], "not_utf8")

    def test_anchors_missing_skips_model(self):
        docs = b"Nothing about throttling here.\n"
        self.assertEqual(self.go(docs=docs, llm=no_llm)["reason"], "anchors_not_in_docs")

    def test_ungrounded_answer_is_unknown_not_contradicted(self):
        r = self.go(llm=lambda t, i: answer("5", quote="The API rate limit is 5 requests per minute."))
        self.assertEqual((r["verdict"], r["reason"]), ("UNKNOWN", "llm_quote_not_in_docs"))

    def test_report_is_canonical_and_stable(self):
        self.assertEqual(C.canonical(self.go()), C.canonical(self.go()))
        self.assertNotIn("quote", json.loads(C.canonical(self.go())))


class UrlStaleTests(unittest.TestCase):
    def test_urls(self):
        C.check_url("https://raw.githubusercontent.com/o/r/main/docs/x.md", "raw.githubusercontent.com")
        for bad in ["http://raw.githubusercontent.com/x", "https://evil.com/x", "https://raw.githubusercontent.com@evil.com/x",
                    "https://raw.githubusercontent.com:81/x", "https://raw.githubusercontent.com/x?a=1", "https://raw.githubusercontent.com"]:
            with self.assertRaises(gl.vm.UserError, msg=bad):
                C.check_url(bad, "raw.githubusercontent.com")

    def test_stale(self):
        c = {"status": "VERIFIED", "last_verified_at": 1000, "max_age": 100}
        self.assertFalse(C.is_stale(c, 1100))
        self.assertTrue(C.is_stale(c, 1101))
        self.assertFalse(C.is_stale({**c, "status": "CONTRADICTED"}, 5000))


if __name__ == "__main__":
    unittest.main()
