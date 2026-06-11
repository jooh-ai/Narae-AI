"""웹 챗봇 서버 (9단계).

서버 1대에서 이 앱을 실행하면, 직원들은 브라우저로 접속해 사내 규정을 질문한다.
- GET  /          : 챗 화면(HTML)
- POST /api/ask   : 질문 -> 답변+출처 (JSON)

실행:
    python -m scripts.serve            # 또는
    uvicorn src.web.app:app --host 0.0.0.0 --port 8000

직원은 브라우저에서  http://<서버주소>:8000  으로 접속.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import config
from src.rag.chain import RagChain

app = FastAPI(title="사내 규정 챗봇")

# 무거운 인덱스/모델은 서버 시작 시 한 번만 로드해 재사용
_chain: RagChain | None = None


def get_chain() -> RagChain:
    global _chain
    if _chain is None:
        _chain = RagChain()
    return _chain


class AskRequest(BaseModel):
    question: str


@app.on_event("startup")
def _startup() -> None:
    # 첫 요청 지연을 막기 위해 시작 시 미리 로드 (인덱스 없으면 명확히 안내)
    try:
        get_chain()
    except FileNotFoundError as e:
        print(f"\n⚠️  {e}\n")


@app.post("/api/ask")
def ask(req: AskRequest) -> JSONResponse:
    question = req.question.strip()
    if not question:
        return JSONResponse({"answer": "질문을 입력하세요.", "sources": []})
    answer = get_chain().ask(question)
    return JSONResponse(
        {
            "answer": answer.text,
            "sources": [
                {"citation": c.citation, "score": round(s, 3)} for c, s in answer.sources
            ],
        }
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _PAGE


# --- 브라우저에 보여줄 단일 페이지(별도 파일 없이 내장) ---------------------
_PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>사내 규정 챗봇</title>
<style>
  body { font-family: -apple-system, "Segoe UI", sans-serif; max-width: 760px;
         margin: 0 auto; padding: 20px; background:#f5f6f8; color:#1c1e21; }
  h1 { font-size: 20px; }
  #log { background:#fff; border:1px solid #ddd; border-radius:10px; padding:16px;
         height: 56vh; overflow-y:auto; }
  .msg { margin:10px 0; line-height:1.5; }
  .q { text-align:right; }
  .q .bubble { background:#0b66ff; color:#fff; }
  .a .bubble { background:#eef0f3; color:#1c1e21; }
  .bubble { display:inline-block; padding:10px 14px; border-radius:14px;
            white-space:pre-wrap; max-width:85%; }
  .src { font-size:12px; color:#666; margin-top:6px; }
  #bar { display:flex; gap:8px; margin-top:12px; }
  #q { flex:1; padding:12px; border:1px solid #ccc; border-radius:10px; font-size:15px; }
  button { padding:12px 18px; border:0; border-radius:10px; background:#0b66ff;
           color:#fff; font-size:15px; cursor:pointer; }
  button:disabled { opacity:.5; }
</style>
</head>
<body>
  <h1>🏢 사내 규정 챗봇</h1>
  <div id="log"></div>
  <div id="bar">
    <input id="q" placeholder="예) 연차휴가는 며칠인가요?" autofocus
           onkeydown="if(event.key==='Enter')send()">
    <button id="btn" onclick="send()">전송</button>
  </div>
<script>
const log = document.getElementById('log');
function add(text, cls, sources){
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + cls;
  const b = document.createElement('div');
  b.className = 'bubble';
  b.textContent = text;
  wrap.appendChild(b);
  if(sources && sources.length){
    const s = document.createElement('div');
    s.className = 'src';
    s.textContent = '📚 ' + sources.map(x => x.citation + ' (' + x.score + ')').join('  ·  ');
    wrap.appendChild(s);
  }
  log.appendChild(wrap);
  log.scrollTop = log.scrollHeight;
}
async function send(){
  const input = document.getElementById('q');
  const btn = document.getElementById('btn');
  const q = input.value.trim();
  if(!q) return;
  add(q, 'q');
  input.value = '';
  btn.disabled = true;
  try{
    const r = await fetch('/api/ask', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question:q})
    });
    const d = await r.json();
    add(d.answer, 'a', d.sources);
  }catch(e){
    add('서버 오류가 발생했습니다.', 'a');
  }finally{
    btn.disabled = false;
    input.focus();
  }
}
</script>
</body>
</html>"""
