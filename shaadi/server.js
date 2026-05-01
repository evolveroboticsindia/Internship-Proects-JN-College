const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

app.post("/ask", async (req, res) => {
  const { prompt } = req.body;

  try {
    const response = await fetch("http://localhost:11434/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "phi3",
        prompt: prompt,
        stream: false
      })
    });

    const data = await response.json();
    res.json({ reply: data.response });

  } catch (err) {
    res.json({ reply: "Error talking to AI" });
  }
});

app.listen(3000, () => {
  console.log("Server running on http://localhost:3000");
});