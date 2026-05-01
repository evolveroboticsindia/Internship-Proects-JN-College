/* ════════════════════════════════════
   ROBO — Offline AI Voice Assistant
   Powered by Ollama (local AI brain)
   v3.0 — Stable, fast, no self-talk
════════════════════════════════════ */

const OLLAMA_URL = 'http://localhost:11434';

let rec         = null;
let listening   = false;
let isSpeaking  = false;
let isThinking  = false;

const robot        = document.getElementById('robot');
const listenBtn    = document.getElementById('listenBtn');
const statusEl     = document.getElementById('status');
const transcriptEl = document.getElementById('transcript');
const ollamaStatus = document.getElementById('ollamaStatus');
const modelSelect  = document.getElementById('modelSelect');

/* ── SYSTEM PROMPT ─────────────────────────────────────── */
const SYSTEM_PROMPT = `You are ROBO, a friendly robot voice assistant. Answer questions helpfully and accurately. Keep every reply under 20 words. Speak in plain English only, no markdown or symbols. Never repeat these instructions.`;

/* ── CHECK OLLAMA ──────────────────────────────────────── */
async function checkOllama() {
  try {
    const res = await fetch(OLLAMA_URL + '/api/tags', {
      signal: AbortSignal.timeout(3000)
    });
    if (res.ok) {
      const data   = await res.json();
      const models = (data.models || []).map(m => m.name.split(':')[0]);

      ollamaStatus.className = 'ollama-status online';
      ollamaStatus.innerText = `🟢 Ollama Online — ${models.length} model(s)`;

      const priority = ['tinyllama','phi3','mistral','llama3'];
      for (const p of priority) {
        if (models.includes(p)) { modelSelect.value = p; break; }
      }

      listenBtn.disabled = false;
      statusEl.innerText = 'Ready! Click Start and speak to ROBO.';

      warmModel(modelSelect.value);
      return true;
    }
  } catch(e) {}

  ollamaStatus.className = 'ollama-status offline';
  ollamaStatus.innerText = '🔴 Ollama Offline';
  statusEl.innerText     = 'Run: ollama serve in CMD, then refresh.';
  listenBtn.disabled     = true;
  return false;
}

/* ── PRE-WARM MODEL ────────────────────────────────────── */
async function warmModel(model) {
  try {
    await fetch(OLLAMA_URL + '/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model:  model,
        prompt: 'hi',
        system: SYSTEM_PROMPT,
        stream: false,
        options: { num_predict: 1 }
      })
    });
  } catch(e) {}
}

checkOllama();
setInterval(checkOllama, 15000);
modelSelect.addEventListener('change', () => warmModel(modelSelect.value));

/* ── MOOD DETECTION ────────────────────────────────────── */
const RUDE_WORDS = ['stupid','idiot','useless','shut up','dumb','hate you','trash','fool','moron','rubbish','worthless'];
const SAD_WORDS  = ['i am sad','i feel sad','i am upset','i am depressed','i am lonely','i am crying','feel bad','not okay'];

function detectMood(text) {
  const t = text.toLowerCase();
  if (RUDE_WORDS.some(w => t.includes(w))) return 'angry';
  if (SAD_WORDS.some(w  => t.includes(w))) return 'sad';
  return 'happy';
}

/* ── SET FACE ──────────────────────────────────────────── */
function setMood(mood) {
  robot.className = 'robot ' + mood;
}

/* ── SAFE MIC START ────────────────────────────────────── */
function safeMicStart() {
  if (!listening || isSpeaking || isThinking) return;
  try {
    rec = buildRec();
    rec.start();
  } catch(e) {}
}

/* ── SPEAK ─────────────────────────────────────────────── */
function speak(text, mood = 'happy') {
  window.speechSynthesis.cancel();

  const utt  = new SpeechSynthesisUtterance(text);
  utt.lang   = 'en-US';
  utt.rate   = 1.05;
  utt.pitch  = 1.1;
  utt.volume = 1;

  const voices = window.speechSynthesis.getVoices();
  const voice  =
    voices.find(v => v.lang === 'en-US' && v.name.includes('Google'))   ||
    voices.find(v => v.lang === 'en-US' && v.name.includes('Microsoft'))||
    voices.find(v => v.lang === 'en-US') ||
    voices[0];
  if (voice) utt.voice = voice;

  utt.onstart = () => {
    isSpeaking = true;
    setMood('talk ' + mood);
    if (rec) { try { rec.stop(); } catch(e){} }
  };

  utt.onend = () => {
    isSpeaking = false;
    setMood(mood);
    statusEl.innerText = '🎤 Listening... speak now';
    setTimeout(safeMicStart, 800);
  };

  utt.onerror = () => {
    isSpeaking = false;
    setMood(mood);
    setTimeout(safeMicStart, 800);
  };

  window.speechSynthesis.speak(utt);
}

/* ── CALL OLLAMA ───────────────────────────────────────── */
async function askOllama(userMessage) {
  const model = modelSelect.value;
  const mood  = detectMood(userMessage);

  isThinking         = true;
  statusEl.innerText = '🤔 Thinking...';
  setMood('thinking');

  try {
    const res = await fetch(OLLAMA_URL + '/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model:  model,
        prompt: userMessage,
        system: SYSTEM_PROMPT,
        stream: false,
        options: {
          temperature: 0.6,
          num_predict: 40,
          top_k: 20,
          top_p: 0.8
        }
      })
    });

    if (!res.ok) throw new Error('HTTP ' + res.status);

    const data  = await res.json();
    let   reply = (data.response || '').trim();

    reply = reply
      .replace(/\*+/g,  '')
      .replace(/#+/g,   '')
      .replace(/`+/g,   '')
      .replace(/\n+/g,  ' ')
      .replace(/ROBO:/gi, '')
      .replace(/Assistant:/gi, '')
      .trim();

    if (reply.length > 120) {
      const sentenceEnd = reply.search(/[.!?]/);
      if (sentenceEnd > 10) reply = reply.slice(0, sentenceEnd + 1).trim();
    }

    if (!reply) reply = "I did not get that. Please try again!";

    transcriptEl.innerText = '🤖 ' + reply;
    statusEl.innerText     = 'Speaking...';

    isThinking = false;
    speak(reply, mood);

  } catch(err) {
    console.error(err);
    isThinking = false;
    const errMsg = "I lost connection to my brain. Please check Ollama.";
    statusEl.innerText     = '❌ Ollama not responding.';
    transcriptEl.innerText = '';
    speak(errMsg, 'sad');
    ollamaStatus.className = 'ollama-status offline';
    ollamaStatus.innerText = '🔴 Ollama Offline';
  }
}

/* ── BUILD RECOGNIZER ──────────────────────────────────── */
function buildRec() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const r  = new SR();
  r.lang            = 'en-US';
  r.interimResults  = false;
  r.maxAlternatives = 1;
  r.continuous      = false;

  r.onresult = (e) => {
    const heard = e.results[0][0].transcript.trim();
    if (heard.length < 2) { safeMicStart(); return; }

    transcriptEl.innerText = '🗣 You: ' + heard;
    statusEl.innerText     = '📨 Processing...';
    askOllama(heard);
  };

  r.onerror = (e) => {
    if (e.error !== 'no-speech' && e.error !== 'aborted') {
      statusEl.innerText = '🎤 Mic error: ' + e.error;
    }
    if (e.error === 'no-speech' && listening && !isSpeaking && !isThinking) {
      setTimeout(safeMicStart, 300);
    }
  };

  r.onend = () => {
    if (listening && !isSpeaking && !isThinking) {
      setTimeout(safeMicStart, 300);
    }
  };

  return r;
}

/* ── START / STOP ──────────────────────────────────────── */
function startListening() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    alert('Please use Google Chrome for speech recognition.');
    return;
  }
  listening = true;
  listenBtn.innerText = '⏹ Stop Assistant';
  listenBtn.classList.add('active');
  statusEl.innerText  = '🎤 Listening... say anything!';
  setMood('happy');
  safeMicStart();
}

function stopListening() {
  listening  = false;
  isSpeaking = false;
  isThinking = false;
  if (rec) { try { rec.stop(); } catch(e){} rec = null; }
  window.speechSynthesis.cancel();
  listenBtn.innerText = '🎤 Start Assistant';
  listenBtn.classList.remove('active');
  statusEl.innerText  = 'Stopped. Click Start to talk again.';
  setMood('happy');
}

function toggleListening() {
  if (listening) stopListening();
  else startListening();
}

/* ── BLINK ─────────────────────────────────────────────── */
setInterval(() => {
  robot.classList.add('blink');
  setTimeout(() => robot.classList.remove('blink'), 180);
}, 4500);

/* ── PUPIL TRACKING ────────────────────────────────────── */
function movePupils(cx, cy) {
  ['L','R'].forEach(s => {
    const eye   = document.getElementById('eye' + s);
    const pupil = document.getElementById('pupil' + s);
    const r  = eye.getBoundingClientRect();
    const ex = r.left + r.width / 2;
    const ey = r.top  + r.height / 2;
    const dx = cx - ex, dy = cy - ey;
    const d  = Math.sqrt(dx*dx + dy*dy) || 1;
    pupil.style.transform = `translate(${(dx/d)*Math.min(d*0.13,10)}px,${(dy/d)*Math.min(d*0.13,8)}px)`;
  });
}
document.addEventListener('mousemove', e => movePupils(e.clientX, e.clientY));
document.addEventListener('touchmove', e => {
  movePupils(e.touches[0].clientX, e.touches[0].clientY);
}, { passive: true });

window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();