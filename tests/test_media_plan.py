"""Tests for the media plan + Veo ledger (add-video-media-plan). Pure functions; tmp ledger files."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from xlights_orchestrator import veo_ledger
from xlights_orchestrator.media_plan import (
    MediaBudget,
    apply_media,
    asset_groups,
    build_handoff,
    clips_for,
    featured_hits,
    plan,
    procedural_brief,
    summary,
    value_scores,
    veo_prompt,
)
from xlights_orchestrator.video_script import Beat, VideographerOut, constraints_for, resolve_beats

# A 12-section pop song: intro, V1, pre, chorus, V2, pre, chorus, post, bridge, chorus, post, outro.
LABELS = ["intro", "Verse 1", "Pre-Chorus", "Chorus", "Verse 2", "Pre-Chorus", "Chorus",
          "Post-Chorus", "Bridge", "Chorus", "Post-Chorus", "outro"]
DUR_S = [15.7, 28.8, 8.1, 26.9, 18.4, 6.7, 26.9, 17.5, 14.8, 23.3, 7.2, 15.9]
ENERGY = [0.2, 0.4, 0.6, 0.8, 0.4, 0.6, 0.85, 0.7, 0.5, 1.0, 0.7, 0.3]


def sections_from(durs):
    out, t = [], 0
    for d in durs:
        out.append((t, t + int(d * 1000)))
        t += int(d * 1000)
    return out


SECTIONS = sections_from(DUR_S)
B10 = MediaBudget(campaign_clips=10)          # the user's Veo limits: 8 s clips, 10 a day


# -- clip math and grouping --------------------------------------------------------

def test_clips_for_long_section_with_stretch():
    assert clips_for(20_800, 8, 1.2) == 3              # 20.8 s / 9.6 s ⇒ 3
    assert clips_for(9_600, 8, 1.2) == 1               # an exact fit is one clip
    assert clips_for(6_900, 8, 1.2) == 1
    assert clips_for(57_400, 8, 1.2) == 6
    assert clips_for(0, 8, 1.2) == 0


def test_clips_for_rejects_bad_length():
    with pytest.raises(ValueError):
        clips_for(1000, 0, 1.0)


def test_asset_groups_by_label_case_insensitive_and_unlabeled_alone():
    groups = asset_groups(["intro", "Chorus", "verse", "chorus", "", "", "CHORUS"])
    assert groups == [[0], [1, 3, 6], [2], [4], [5]]


def test_only_chorus_family_labels_group():
    """Four 'verse' sections are four different verses (Christmas Canon); a repeated 'bridge' label
    is two different bridges. Only chorus / pre- / post-chorus / refrain / hook / drop return."""
    assert asset_groups(["verse", "verse", "bridge", "bridge"]) == [[0], [1], [2], [3]]
    assert asset_groups(["Pre-Chorus", "Pre-Chorus", "Post-Chorus", "Post-Chorus"]) == [[0, 1], [2, 3]]
    assert asset_groups(["Refrain", "hook", "refrain", "Drop", "drop"]) == [[0, 2], [1], [3, 4]]


# -- value ---------------------------------------------------------------------

def test_value_climax_featured_opening_energy():
    v = value_scores([0.3, 1.0, 0.2], {2: 1})
    assert v[0] == pytest.approx(0.3 + 1.0)            # opening
    assert v[1] == pytest.approx(1.0 + 3.0)            # climax
    assert v[2] == pytest.approx(0.2 + 2.0)            # one featured line


def test_featured_lines_are_capped():
    v = value_scores([0.0, 0.0], {1: 5})
    assert v[1] == pytest.approx(4.0)


def test_featured_hits_match_normalized_text_and_time():
    lyrics = [(12_000, "This dream he had, each child still knows!"), (41_000, "we are waiting")]
    hits = featured_hits(["this dream he had each child still knows", "We Are Waiting", "x"],
                         lyrics, [(0, 10_000), (10_000, 40_000), (40_000, 52_000)])
    assert hits == {1: 1, 2: 1}


# -- the plan -------------------------------------------------------------------

def test_plan_is_deterministic():
    a = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    b = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    assert a == b


def test_climax_group_is_filmed_first():
    p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=3), 10)
    filmed = [s.index for s in p.sections if s.medium == "filmed"]
    assert filmed == [3, 6, 9]                          # the chorus group (climax is section 9)
    assert p.filmed_assets()[0].sections == [3, 6, 9]


def test_choruses_share_one_asset_counted_once():
    p = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    chorus = next(a for a in p.assets if a.sections == [3, 6, 9])
    assert chorus.clips == clips_for(26_900, 8, 1.2) == 3   # the LONGEST member decides
    assert chorus.medium == "filmed" and chorus.promote_rank == 1
    assert all(p.sections[i].asset == chorus.id for i in (3, 6, 9))
    assert p.clips_planned <= 10


def test_budget_never_exceeded_and_stops_at_first_miss():
    for budget in range(0, 15):
        p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=budget), 10)
        assert p.clips_planned <= budget
    p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=4), 10)
    # chorus (3 clips) fits; the next by value needs more than 1 clip ⇒ nothing slips in below it
    assert [a.sections for a in p.filmed_assets()] == [[3, 6, 9]]


def test_zero_budget_is_all_procedural():
    p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=0), 10)
    assert all(s.medium == "procedural" for s in p.sections)
    assert p.clips_planned == 0 and p.veo_seconds == 0 and p.filmed_assets() == []
    assert p.renderable_today == 0


def test_pinned_sections_filmed_first_then_by_value():
    p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=5, pinned=[11]), 10)
    ranks = {tuple(a.sections): a.promote_rank for a in p.filmed_assets()}
    assert ranks[(11,)] == 1                            # outro pinned ⇒ first
    assert ranks[(3, 6, 9)] == 2                        # then the climax group (2 + 3 = 5 clips)


def test_pinned_over_budget_refuses():
    with pytest.raises(ValueError, match="pinned section 3"):
        plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=2, pinned=[3]), 10)
    with pytest.raises(ValueError, match="out of range"):
        plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=5, pinned=[99]), 10)


def test_exhausted_ledger_leaves_filmed_sections_unchanged():
    full = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    empty = plan(SECTIONS, LABELS, ENERGY, {}, B10, 0)
    assert [s.medium for s in full.sections] == [s.medium for s in empty.sections]
    assert full.renderable_today >= 1 and empty.renderable_today == 0


def test_renderable_today_follows_promote_order():
    p = plan(SECTIONS, LABELS, ENERGY, {}, B10, 4)
    # chorus asset (3 clips) fits in 4; the second asset would need more than 1 ⇒ exactly one
    assert p.renderable_today == 1


def test_priced_and_unpriced_estimate():
    p = plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=3), 10, per_second_usd=0.5)
    assert p.veo_seconds == 24 and p.est_usd == pytest.approx(12.0)
    assert plan(SECTIONS, LABELS, ENERGY, {}, MediaBudget(campaign_clips=3), 10).est_usd is None


def test_plan_rejects_mismatched_inputs():
    with pytest.raises(ValueError):
        plan(SECTIONS, LABELS[:-1], ENERGY, {}, B10, 10)


# -- applying to shots + hand-off -----------------------------------------------

def _out(n):
    return VideographerOut(logline="l", motifs=["lantern"], beats=[
        Beat(section_index=i, title=f"b{i}", imagery="wrinkled hands pass a lantern", action="snow falls",
             camera="slow push-in", lighting="gold on blue", procedural_stand_in="a lantern glows in snow")
        for i in range(n)])


def test_apply_media_stamps_shots_and_handoff_uses_resolved_numbers():
    p = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    c = constraints_for(1024, 768, 50, SECTIONS[-1][1])
    shots = resolve_beats(_out(12), SECTIONS, frame_ms=50, labels=LABELS, energies=ENERGY)
    apply_media(shots, p)
    assert shots[3].medium == "filmed" and shots[3].clips == 3 and shots[3].promote_rank == 1
    # Verse 1 (value 0.4, 3 clips) is past the budget ⇒ procedural; the opening got filmed by value.
    assert shots[1].medium == "procedural" and shots[1].clips == 0 and shots[1].promote_rank is None
    h = build_handoff(shots, ["deep blue", "gold"], c)
    assert [x.shot_index for x in h] == list(range(12))
    assert h[3].start_ms == SECTIONS[3][0] and h[3].frames == shots[3].frames
    assert "hands" in h[3].veo_prompt and "No text" in h[3].veo_prompt
    assert h[3].procedural_brief.startswith("a lantern glows in snow")       # the stand-in, not the film
    assert "wrinkled hands" not in h[3].procedural_brief
    assert h[1].veo_prompt == "" and f"{shots[1].frames} frames at 20 fps" in h[1].procedural_brief
    assert "deep blue, gold" in h[1].procedural_brief


def test_procedural_brief_falls_back_to_the_beat_without_a_stand_in():
    c = constraints_for(1024, 768, 50, 52_000)
    sh = resolve_beats(_out(1), [(0, 10_000)], frame_ms=50)[0]
    sh.medium, sh.beat.procedural_stand_in = "procedural", ""
    assert procedural_brief(sh, [], c).startswith("wrinkled hands pass a lantern")
    assert "4:3" in veo_prompt(sh, c)


def test_summary_counts():
    p = plan(SECTIONS, LABELS, ENERGY, {}, B10, 10)
    s = summary(p)
    assert s.filmed_sections + s.procedural_sections == 12
    assert s.clips_planned == p.clips_planned and s.campaign_clips == 10


# -- the ledger -----------------------------------------------------------------

TZ = "America/Los_Angeles"
NOW = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)        # 13:00 Pacific


def _entry(day_ts, song="s1", n=0):
    return veo_ledger.new_entry(clip_id=f"c{n}", song_key=song, asset="A1", seconds=8, tz=TZ, now=day_ts)


def test_remaining_counts_across_songs(tmp_path):
    p = tmp_path / "veo_ledger.jsonl"
    for i in range(7):
        veo_ledger.append(_entry(NOW, "song-a", i), p)
    for i in range(2):
        veo_ledger.append(_entry(NOW, "song-b", 10 + i), p)
    assert veo_ledger.remaining_today(10, TZ, path=p, now=NOW) == 1


def test_yesterday_does_not_count(tmp_path):
    p = tmp_path / "veo_ledger.jsonl"
    yesterday = datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc)
    for i in range(10):
        veo_ledger.append(_entry(yesterday, n=i), p)
    assert veo_ledger.remaining_today(10, TZ, path=p, now=NOW) == 10


def test_missing_ledger_is_full_quota_and_creates_nothing(tmp_path):
    p = tmp_path / "veo_ledger.jsonl"
    assert veo_ledger.remaining_today(10, TZ, path=p, now=NOW) == 10
    assert not p.exists()


def test_day_boundary_is_the_configured_zone():
    # 06:30 UTC on the 11th is still the 10th in Los Angeles (23:30 PDT); 07:30 UTC is the 11th.
    assert veo_ledger.day_for(datetime(2026, 10, 11, 6, 30, tzinfo=timezone.utc), TZ) == "2026-10-10"
    assert veo_ledger.day_for(datetime(2026, 10, 11, 7, 30, tzinfo=timezone.utc), TZ) == "2026-10-11"
    assert veo_ledger.day_for(datetime(2026, 10, 11, 6, 30, tzinfo=timezone.utc), "UTC") == "2026-10-11"


def test_ledger_round_trips_and_skips_bad_lines(tmp_path, caplog):
    p = tmp_path / "veo_ledger.jsonl"
    veo_ledger.append(_entry(NOW), p)
    p.write_text(p.read_text() + "not json\n")
    entries = veo_ledger.read(p)
    assert len(entries) == 1 and entries[0].day == "2026-10-11" and entries[0].seconds == 8
    assert "skipped" in caplog.text


def test_remaining_never_negative(tmp_path):
    p = tmp_path / "veo_ledger.jsonl"
    for i in range(12):
        veo_ledger.append(_entry(NOW, n=i), p)
    assert veo_ledger.remaining_today(10, TZ, path=p, now=NOW) == 0
