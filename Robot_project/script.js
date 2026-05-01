const face = document.getElementById("face");
const statusText = document.getElementById("status");

function setState(state) {
  face.className = "face " + state;
  statusText.innerText = state;
}

// 🎤 Speech Recognition
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SR) {
  alert("Use Chrome browser");
}

const recognition = new SR();

recognition.lang = "en-US";
recognition.interimResults = false;
recognition.maxAlternatives = 1;
recognition.continuous = false;

// 🔒 FIX: prevent multiple starts
let isListening = false;

// 🔊 AUDIO ENABLE
let audioEnabled = false;

document.body.addEventListener("click", () => {
  audioEnabled = true;
  console.log("🔊 Audio enabled");

  speechSynthesis.speak(new SpeechSynthesisUtterance("Ready"));

  startListening();

}, { once: true });

// 🔊 VOICES
let voices = [];

function loadVoices() {
  voices = speechSynthesis.getVoices();
}
loadVoices();
speechSynthesis.onvoiceschanged = loadVoices;

// 🔊 SPEAK
function speak(text) {
  if (!audioEnabled) return;

  speechSynthesis.cancel();

  const speech = new SpeechSynthesisUtterance(text);

  if (voices.length > 0) {
    speech.voice =
      voices.find(v => v.name.includes("Google")) ||
      voices.find(v => v.lang === "en-US") ||
      voices[0];
  }

  speech.rate = 0.95;
  speech.pitch = 1;

  speech.onstart = () => {
    setState("speaking");
    isListening = false; // 🔥 stop listening while speaking
  };

  speech.onend = () => {
    setTimeout(startListening, 400);
  };

  speech.onerror = () => {
    setTimeout(startListening, 400);
  };

  speechSynthesis.speak(speech);
}

// 🔁 START LISTENING (SAFE)
function startListening() {
  if (isListening) return; // 🔥 prevent double start

  setState("listening");

  try {
    recognition.start();
    isListening = true;
  } catch (e) {
    console.log("Start blocked:", e);
  }
}

// 🔥 MAIN FLOW
recognition.onresult = async (event) => {
  const text = event.results[0][0].transcript.trim();

  console.log("You:", text);

  if (!text || text.length < 2) {
    isListening = false;
    startListening();
    return;
  }

  isListening = false;
  setState("thinking");

  try {
    const res = await fetch("http://127.0.0.1:8000/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ text })
    });

    const data = await res.json();

    console.log("AI:", data.reply);

    speak(data.reply);

  } catch (err) {
    console.log("Fetch error:", err);
    setState("error");
    setTimeout(startListening, 1000);
  }
};

// 🔥 RESET STATE WHEN MIC STOPS
recognition.onend = () => {
  isListening = false;
};

// ⚠️ ERROR HANDLING
recognition.onerror = (e) => {
  console.log("Mic error:", e.error);

  isListening = false;

  if (e.error === "not-allowed") {
    alert("Allow microphone access");
    return;
  }

  setTimeout(startListening, 500);
};