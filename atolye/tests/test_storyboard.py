import unittest

from atolye.brand import parse_brand
from atolye.brief import parse_brief
from atolye.issues import ERROR, WARNING
from atolye.storyboard import parse_storyboard, timeline, validate_storyboard

from .helpers import board, brand, brief, messages

BRAND = parse_brand(brand())
BRIEF = parse_brief(brief())


def check(data, b=BRAND, br=BRIEF):
    return validate_storyboard(data, b, br)


def scene(**kw):
    s = {"id": "x", "duration": 2}
    s.update(kw)
    return s


class StoryboardValidationTests(unittest.TestCase):
    def test_valid_board(self):
        self.assertEqual(check(board()), [])

    def test_unknown_format_and_fps(self):
        errs = messages(check(board(format="sinema", fps=29)), ERROR)
        self.assertTrue(any("storyboard.format" in m for m in errs))
        self.assertTrue(any("storyboard.fps" in m for m in errs))

    def test_empty_scenes(self):
        self.assertTrue(messages(check(board(scenes=[])), ERROR))

    def test_duplicate_ids_and_bad_duration(self):
        errs = messages(check(board(scenes=[scene(), scene(), scene(id="y", duration=0)])), ERROR)
        self.assertTrue(any("tekrar" in m for m in errs))
        self.assertTrue(any("duration" in m for m in errs))

    def test_too_long_for_format(self):
        errs = messages(check(board(format="bumper", scenes=[
            scene(id="a", duration=4, show_logo=True), scene(id="b", duration=3, cta=True)])), ERROR)
        self.assertTrue(any("en çok 6" in m for m in errs))

    def test_unknown_color_role(self):
        errs = messages(check(board(scenes=[scene(background="mor", show_logo=True)])), ERROR)
        self.assertTrue(any("'mor'" in m for m in errs))

    def test_headline_contrast_uses_large_text_threshold(self):
        b = brand(); b["colors"]["grey"] = "#949494"  # beyaz üstünde ~3.0: başlık geçer, gövde geçmez
        parsed = parse_brand(b)
        ok = check(board(scenes=[scene(foreground="grey", headline="Başlık", show_logo=True, cta=True)]), parsed)
        self.assertEqual(messages(ok, ERROR), [])
        bad = check(board(scenes=[scene(foreground="grey", body="Gövde metni", show_logo=True, cta=True)]), parsed)
        self.assertTrue(any("gövde kontrastı" in m for m in messages(bad, ERROR)))

    def test_forbidden_words_in_copy(self):
        errs = messages(check(board(scenes=[scene(headline="Şehrin EN İYİ uygulaması",
                                                  show_logo=True, cta=True)])), ERROR)
        self.assertTrue(any("en iyi" in m for m in errs))

    def test_reading_speed_warning(self):
        warns = messages(check(board(scenes=[scene(duration=1, body="bir iki üç dört beş",
                                                   show_logo=True, cta=True)])), WARNING)
        self.assertTrue(any("okunmaz" in m for m in warns))

    def test_logo_must_appear_early_in_short_form(self):
        warns = messages(check(board(scenes=[scene(id="a", duration=4),
                                             scene(id="b", duration=2, show_logo=True, cta=True)])), WARNING)
        self.assertTrue(any("marka ilk" in m for m in warns))

    def test_no_logo_rule_for_long_form(self):
        b = brief(channels=["youtube"])
        warns = messages(check(board(format="youtube", scenes=[scene(cta=True)]), BRAND, parse_brief(b)), WARNING)
        self.assertFalse(any("marka ilk" in m for m in warns))

    def test_missing_cta_and_channel_mismatch_warn(self):
        warns = messages(check(board(format="story", scenes=[scene(show_logo=True)])), WARNING)
        self.assertTrue(any("CTA" in m for m in warns))
        self.assertTrue(any("kanalları" in m for m in warns))

    def test_bad_transition(self):
        errs = messages(check(board(scenes=[scene(transition="wipe", show_logo=True, cta=True)])), ERROR)
        self.assertTrue(any("transition" in m for m in errs))

    def test_runs_without_brand_or_brief(self):
        self.assertEqual(messages(validate_storyboard(board(), None, None), ERROR), [])


class TimelineTests(unittest.TestCase):
    def test_frames_are_contiguous_and_rounding_does_not_drift(self):
        data = board(fps=30, scenes=[scene(id=str(i), duration=1 / 3) for i in range(9)])
        tl = timeline(parse_storyboard(data))
        for prev, nxt in zip(tl, tl[1:]):
            self.assertEqual(prev.end_frame, nxt.start_frame)
            self.assertEqual(prev.end, nxt.start)
        self.assertEqual(tl[-1].end_frame, 90)
        self.assertEqual(sum(t.frames for t in tl), 90)

    def test_start_end(self):
        tl = timeline(parse_storyboard(board()))
        self.assertEqual([(t.start, t.end) for t in tl], [(0, 2), (2, 5)])
        self.assertEqual([(t.start_frame, t.end_frame) for t in tl], [(0, 60), (60, 150)])


if __name__ == "__main__":
    unittest.main()
