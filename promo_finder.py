"""Kuku Promo Finder: deterministic screenplay-first promo shortlisting.

Run:
  python promo_finder.py --input-dir ./screenplays --output-dir ./outputs
The parser expects the timestamped .txt screenplay format in the assignment.
"""
import argparse, csv, json, re
from pathlib import Path

TIME = r"(\d{2}:\d{2}\.\d{2})"
HOOK_PATTERNS = [
    r"\b(slaps?|strikes?|hits?|punch(?:es|ed)?|shoots?|stab(?:s|bed)?|explod(?:es|ing)|crash(?:es|ed)?|screams?|shouts?|slam(?:s|med)?|bursts? open|kicks? open|collaps(?:es|ed)|falls? unconscious|blood|fire|burn(?:s|ing|ed)?|brand(?:s|ed)?|chokes?|grabs?|seizes?|arrest|dead|dying|poison|betray(?:s|ed|al)?|wedding|bride|groom|secret|reveal(?:s|ed)?|recogniz(?:es|ed)|identity|who are you|you are|imposter|witchcraft)\b",
    r"[!?]"
]
CLIFF_PATTERNS = [
    r"\b(but|until|before|unless|wait|stop|who|what|why|how|never|cannot|can't|won't|must|secret|truth|reveal|identity|arrest|kill|execute|burn|poison|guilty|innocent|betray|door|footsteps|enters?|arrives?|appears?|interrupts?|suddenly|just then|orders?|threatens?|promises?|swears?|demands?|refuses?|denies?|wedding|marriage|license|council|trial|sentence|hang|gallows|explosion|blast)\b",
    r"[!?…]$"
]

def seconds(ts):
    mm, ss = ts.split(":")
    return int(mm) * 60 + float(ss)

def timestamp(value):
    mm = int(value // 60)
    ss = value - mm * 60
    return f"{mm:02d}:{ss:05.2f}"

def parse_file(path):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    em = re.search(r"EPISODE NUMBER:\s*Episode\s*(\d+)", raw)
    if not em:
        raise ValueError(f"Episode number not found in {path}")
    lm = re.search(r"EPISODE LOGLINE:\s*(.*)", raw)
    events, label = [], "EVENT"
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        lab = re.match(r"\*\*(.+?):\*\*", line.strip())
        if lab:
            label = lab.group(1).strip()
        tm = re.search(r"Start:\s*\((" + TIME + r")\)\s*\|\s*End:\s*\((" + TIME + r")\)", line)
        if tm:
            start, end = seconds(tm.group(1)), seconds(tm.group(3))
            desc = lines[i+1].strip() if i+1 < len(lines) else ""
            desc = re.sub(r"^\*+|\*+$", "", desc).strip()
            if end > start:
                events.append({"start":start,"end":end,"label":label,"text":desc})
    return {"episode":int(em.group(1)), "logline":lm.group(1).strip() if lm else "", "events":events}

EXCERPT_CHARS = 450
SENT_END = re.compile(r"[.!?][\"']?\s")

def head_excerpt(text, limit=EXCERPT_CHARS):
    """First part of a text, cut back to a full sentence and marked when shortened."""
    text = text.strip()
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    ms = list(SENT_END.finditer(cut))
    if ms and ms[-1].end() > 40:
        cut = cut[:ms[-1].end()].rstrip()
    return cut + " […]", True

def tail_excerpt(text, limit=EXCERPT_CHARS):
    """Last part of a text (the cliffhanger is the final line), starting at a sentence boundary."""
    text = text.strip()
    if len(text) <= limit:
        return text, False
    cut = text[-limit:]
    ms = list(SENT_END.finditer(cut))
    if ms and ms[0].end() < len(cut) - 40:
        cut = cut[ms[0].end():].lstrip()
    return "[…] " + cut, True

def joined(events, a, b):
    return " ".join(e["text"] for e in events if e["start"] < b and e["end"] > a)

def cue(text, patterns):
    text = text.lower()
    return min(1.0, sum(len(re.findall(p,text)) for p in patterns)*0.23)

def score(ep, a, b):
    ev = ep["events"]
    opening = joined(ev,a,min(a+3,b))
    ending = joined(ev,max(a,b-5),b)
    body = joined(ev,a,b)
    hook, cliff = cue(opening,HOOK_PATTERNS), cue(ending,CLIFF_PATTERNS)
    first=[e for e in ev if e["start"]<a+3 and e["end"]>a]
    last=[e for e in ev if e["start"]<b and e["end"]>b-5]
    visual=min(1.0,sum(e["label"] in ("CAMERA","ACTION","SOUND FX") for e in first)*.35)
    endvisual=min(1.0,sum(e["label"] in ("CAMERA","ACTION","SOUND FX") for e in last)*.30)
    standalone=.55
    low=body.lower()
    if any(w in low for w in ("lady juliana","alexander","catherine","rupert","duchess")): standalone+=.20
    if any(w in low for w in ("because","my husband","my mother","your grace","your duke","my lord")): standalone+=.10
    if len(body.split())>35: standalone+=.10
    standalone=min(1.0,standalone)
    duration_fit=max(0.0,1-abs((b-a)-38)/45)
    total=100*(.31*hook+.30*cliff+.19*standalone+.10*visual+.06*endvisual+.04*duration_fit)
    if re.search(r"\b(thank you|good morning|yes,? my lord|of course|very well)\b",opening.lower()): total-=5
    if re.search(r"\b(we are safe|it is over|thank you|i forgive you|i love you)\b",ending.lower()): total-=8
    return total,hook,cliff,standalone,opening,ending,body

def run(files):
    episodes=[parse_file(f) for f in files]
    candidates=[]
    for ep in episodes:
        times=sorted(set([e["start"] for e in ep["events"]]+[e["end"] for e in ep["events"]]))
        for a in times:
            for b in times:
                if not 20 <= b-a <= 60: continue
                s,h,c,st,op,en,body=score(ep,a,b)
                if s>=24:
                    op_txt, op_cut = head_excerpt(op)
                    en_txt, en_cut = tail_excerpt(en)
                    bd_txt, bd_cut = head_excerpt(body, 900)
                    candidates.append({"episode":ep["episode"],"start":round(a,2),"end":round(b,2),
                      "duration_seconds":round(b-a,2),"score":round(s,2),"hook_score":round(h,2),
                      "cliffhanger_score":round(c,2),"standalone_proxy_score":round(st,2),
                      "opening_evidence":op_txt,"ending_evidence":en_txt,
                      "evidence_excerpt":bd_txt,"opening_shortened":op_cut,"ending_shortened":en_cut,
                      "excerpt_capped":op_cut or en_cut or bd_cut,
                      "episode_logline":ep["logline"]})
    DEDUP_OVERLAP_RATIO = 0.40
    def overlap_of_shorter(x, y):
        if x["episode"] != y["episode"]:
            return 0.0
        inter = max(0.0, min(x["end"], y["end"]) - max(x["start"], y["start"]))
        return inter / min(x["end"] - x["start"], y["end"] - y["start"])

    selected = []
    for epn in sorted(e["episode"] for e in episodes):
        group = sorted([r for r in candidates if r["episode"] == epn], key=lambda r: r["score"], reverse=True)
        kept = []
        for r in group:
            if all(overlap_of_shorter(r, q) <= DEDUP_OVERLAP_RATIO for q in kept):
                kept.append(r)
            if len(kept) == 3:
                break
        selected.extend(kept)
    selected.sort(key=lambda r:r["score"],reverse=True)
    final = []
    for r in selected:
        if all(overlap_of_shorter(r, q) <= DEDUP_OVERLAP_RATIO for q in final):
            final.append(r)
    selected = final
    for i,r in enumerate(selected,1):
        r["rank"]=i
        r["segments"]=[{"episode":r["episode"],"start":timestamp(r["start"]),"end":timestamp(r["end"])}]
        r["hook"]=r["opening_evidence"] or "Opening cue detected by screenplay parser."
        r["cliffhanger"]=r["ending_evidence"] or "Ending cue detected by screenplay parser."
        notes = []
        if r["hook_score"] < 0.5: notes.append(f"weak hook cue ({r['hook_score']:.2f})")
        if r["cliffhanger_score"] < 0.5: notes.append(f"weak cliffhanger cue ({r['cliffhanger_score']:.2f})")
        if r.get("opening_shortened"): notes.append("opening text shortened to its first full sentences")
        if r.get("ending_shortened"): notes.append("ending text shown as its last 450 characters; earlier text omitted")
        def _words(t, n):
            w = t.replace("[…]", " ").split()
            return " ".join(w[:n]) + ("…" if len(w) > n else "")
        def _last_words(t, n):
            w = t.replace("[…]", " ").split()
            return ("…" if len(w) > n else "") + " ".join(w[-n:])
        opens = _words(r["opening_evidence"], 12)
        ends = _last_words(r["ending_evidence"], 12)
        r["why_it_works"] = (f"Opens: \"{opens}\" Ends: \"{ends}\" "
                             f"(hook {r['hook_score']:.2f}, cliffhanger {r['cliffhanger_score']:.2f}, "
                             f"standalone {r['standalone_proxy_score']:.2f}, {r['duration_seconds']:.1f}s). "
                             + ("Editor check: " + "; ".join(notes) + "." if notes else "Editor must confirm the ending is unresolved on screen."))
        r["data_notes"] = "; ".join(notes)
        r["review_status"]="Automated shortlist — editor review required"
    return episodes,candidates,selected

def write_outputs(files, output_dir):
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    episodes,candidates,selected=run(files)
    (out/"ranked_shortlist.json").write_text(json.dumps(selected,indent=2,ensure_ascii=False),encoding="utf-8")
    (out/"run_audit.json").write_text(json.dumps({
      "input_files":len(files),"episodes_parsed":len(episodes),
      "timeline_events_parsed":sum(len(e["events"]) for e in episodes),
      "candidate_windows_generated":len(candidates),"shortlist_count":len(selected),
      "duration_seconds":[20,60],"score_is_probability":False,
      "limitations":["screenplay only; no video/audio inspection","one continuous segment per promo",
        "standalone clarity is a proxy","human review required"]
    },indent=2),encoding="utf-8")
    with (out/"all_candidates.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=list(candidates[0].keys()) if candidates else ["episode","start","end","score"]
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(candidates)
    with (out/"shortlist.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["rank","episode","start","end","duration_seconds","score","hook_score","cliffhanger_score","standalone_proxy_score","hook","cliffhanger","why_it_works","data_notes","review_status"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in selected:
            row={k:r.get(k,"") for k in fields}
            row["start"],row["end"]=timestamp(r["start"]),timestamp(r["end"])
            w.writerow(row)
    return episodes,candidates,selected

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",required=True)
    ap.add_argument("--output-dir",default="outputs")
    args=ap.parse_args()
    files=sorted(Path(args.input_dir).glob("*.txt"))
    if not files: raise SystemExit("No .txt screenplay files found.")
    eps,cands,selected=write_outputs(files,args.output_dir)
    print(f"Parsed {len(eps)} episodes / {sum(len(e['events']) for e in eps)} events.")
    print(f"Generated {len(cands)} candidate windows; retained {len(selected)} non-duplicate shortlist rows.")
