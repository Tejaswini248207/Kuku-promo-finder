import streamlit as st
from pathlib import Path
import tempfile, zipfile, io, csv
from promo_finder import run, timestamp

st.set_page_config(page_title="Kuku Promo Finder", page_icon="🎬", layout="wide")
st.title("Kuku Promo Finder")
st.caption("Screenplay-first promo shortlisting • 20–60 seconds • human editorial review required")
st.info("This tool ranks candidate moments from timestamped screenplays. It does not inspect the finished video, verify audio, or guarantee that a clip is context-free.")
uploads = st.file_uploader("Upload timestamped screenplay .txt files", type=["txt"], accept_multiple_files=True)
if uploads:
    if st.button("Find promo candidates", type="primary"):
        with tempfile.TemporaryDirectory() as td:
            paths=[]
            for f in uploads:
                p=Path(td)/f.name
                p.write_bytes(f.getvalue())
                paths.append(p)
            with st.spinner("Parsing episodes and scoring candidate windows..."):
                eps,cands,selected=run(paths)
            st.success(f"Parsed {len(eps)} episodes and {sum(len(e['events']) for e in eps)} timeline events. Generated {len(cands):,} candidate windows.")
            st.subheader("Top 20 promo candidates")
            for r in selected[:20]:
                with st.expander(f"#{r['rank']} • Episode {r['episode']} • {timestamp(r['start'])}–{timestamp(r['end'])} • score {r['score']:.1f}"):
                    st.write("**Hook evidence (first 3 seconds):**",r["opening_evidence"])
                    st.write("**Cliffhanger evidence (last 5 seconds):**",r["ending_evidence"])
                    st.write("**Episode context:**",r["episode_logline"])
                    st.caption("Score is a heuristic ranking signal, not a probability. Confirm the cut against the video and the following scene.")
            csv_data=io.StringIO()
            fields=["rank","episode","start","end","duration_seconds","score","hook_score","cliffhanger_score","standalone_proxy_score","opening_evidence","ending_evidence","episode_logline"]
            w=csv.DictWriter(csv_data,fieldnames=fields);w.writeheader()
            for r in selected:
                row={k:r.get(k,"") for k in fields}
                row["start"],row["end"]=timestamp(r["start"]),timestamp(r["end"])
                w.writerow(row)
            st.download_button("Download ranked shortlist CSV",csv_data.getvalue(),file_name="promo_shortlist.csv",mime="text/csv")
else:
    st.markdown("Upload one or more screenplay `.txt` files to run the parser. The same engine can be used from the command line for batch runs.")
