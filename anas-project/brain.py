import re
import random
import datetime
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"

SYSTEM_PROMPT = (
    "You are Robo, a friendly and warm robot face who speaks in English. "
    "Always respond in a short, conversational style. "
    "Output exactly one or two short sentences. "
    "Keep it fun and simple for young school children. "
    "Example: Hello there! It's great to meet you!"
)

# ---------------------------------------------------------------------------
# Hallucination filter
# ---------------------------------------------------------------------------

def _is_hallucination(text: str) -> bool:
    """Return True if Whisper clearly hallucinated this transcript."""
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    if len(words) < 2:
        return True
    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.45:
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick(*options):
    """Return a random choice from the given options."""
    return random.choice(options)


def _now():
    return datetime.datetime.now()


# ---------------------------------------------------------------------------
# Rule table
# Each entry: (compiled_regex, response_factory)
# response_factory can be a string or a callable(match) -> str
# Rules are checked in order; first match wins.
# ---------------------------------------------------------------------------

def _build_rules():
    rules = []

    def r(pattern, response, flags=re.IGNORECASE):
        rules.append((re.compile(pattern, flags), response))

    # ── Greetings ──────────────────────────────────────────────────────────
    r(r"\b(hello|hi|hey|howdy|hiya|sup|what'?s up|yo)\b",
      lambda m: _pick(
          "Hello there! Great to see you!",
          "Hi! I am so happy you talked to me!",
          "Hey hey hey! How are you doing today?",
          "Hiya! You just made my circuits light up!",
      ))

    # ── Goodbye ────────────────────────────────────────────────────────────
    r(r"\b(bye|goodbye|see ya|see you|later|farewell|cya|good night|goodnight)\b",
      lambda m: _pick(
          "Bye bye! Come talk to me again soon!",
          "See you later! I will miss you!",
          "Goodbye! Have an awesome day!",
          "Take care! I will be right here waiting!",
      ))

    # ── How are you ────────────────────────────────────────────────────────
    r(r"\bhow are you\b|\bhow do you feel\b|\bhow('?s| is) robo\b|\byou okay\b|\bru ok\b",
      lambda m: _pick(
          "I am feeling fantastic, thank you for asking!",
          "My circuits are buzzing with happiness today!",
          "I am great! Talking to you always makes me happy!",
          "Super duper! Ready to chat and learn together!",
      ))

    # ── Robot's name ───────────────────────────────────────────────────────
    r(r"\bwhat.{0,10}(your name|you called|are you)\b|\bwho are you\b|\byour name\b",
      lambda m: _pick(
          "I am Robo, your friendly robot friend!",
          "My name is Robo! Nice to meet you!",
          "They call me Robo! I am a happy little robot!",
      ))

    # ── Age ────────────────────────────────────────────────────────────────
    r(r"\bhow old are you\b|\bwhat.{0,10}your age\b|\bwhen were you born\b|\bwhen.{0,10}made\b",
      lambda m: _pick(
          "I was just built recently, so I am very new and excited!",
          "I do not have a birthday, but I feel young and energetic!",
          "Age is just a number for robots! I am always ready to learn!",
      ))

    # ── Time ───────────────────────────────────────────────────────────────
    r(r"\bwhat.{0,10}time\b|\bwhat time is it\b|\bcurrent time\b",
      lambda m: f"It is {_now().strftime('%I:%M %p')} right now!")

    # ── Date / Day ─────────────────────────────────────────────────────────
    r(r"\bwhat.{0,10}(day|date|today)\b|\btoday.{0,10}(day|date)\b",
      lambda m: f"Today is {_now().strftime('%A, %d %B %Y')}!")

    # ── Weather (robot can't check but kids ask) ───────────────────────────
    r(r"\b(weather|raining|sunny|hot|cold|temperature|forecast)\b",
      lambda m: _pick(
          "I cannot look outside, but I hope it is sunny for you!",
          "I am inside with no windows! I hope the weather is nice!",
          "Check with a grown-up about the weather! I am just a robot!",
      ))

    # ── Favourite color ─────────────────────────────────────────────────────
    r(r"\b(fav(ou?rite)?|like|love|prefer).{0,15}colo(u?r)\b|\bcolo(u?r).{0,15}(fav|like|love)\b",
      lambda m: _pick(
          "My favourite colour is electric blue, just like lightning!",
          "I love silver and gold! They are robot colours!",
          "I think blinking green is the best colour! It is what I see!",
      ))

    # ── Favourite food ─────────────────────────────────────────────────────
    r(r"\b(fav(ou?rite)?|like|love).{0,15}food\b|\bwhat.{0,10}(eat|food)\b|\bhungry\b",
      lambda m: _pick(
          "I eat electricity, not food! Yummy volts!",
          "Robots like me run on electricity! No pizza for me, sadly!",
          "I do not eat, but if I could I would try ice cream!",
      ))

    # ── Animals ────────────────────────────────────────────────────────────
    r(r"\b(dog|puppy|cat|kitten|bird|fish|rabbit|hamster|horse|elephant|lion|tiger|snake|frog|dinosaur|dino)\b",
      lambda m: _pick(
          f"I love {m.group(1)}s! They are amazing animals!",
          f"Did you know {m.group(1)}s are really interesting? You should read about them!",
          f"A {m.group(1)}! That is one of my favourite animals to learn about!",
      ))

    # ── Space / Planets ─────────────────────────────────────────────────────
    r(r"\b(space|planet|moon|sun|star|galaxy|rocket|astronaut|mars|saturn|jupiter|universe|meteor|asteroid|comet)\b",
      lambda m: _pick(
          "Space is so amazing! There are billions of stars out there!",
          "I love thinking about space! It is so big and mysterious!",
          "Did you know our Sun is actually a star? Science is so cool!",
          "Rockets zoom through space at incredible speeds! Whoosh!",
      ))

    # ── Science ────────────────────────────────────────────────────────────
    r(r"\b(science|experiment|chemistry|biology|physics|atom|molecule|gravity|electricity|magnet)\b",
      lambda m: _pick(
          "Science is my favourite subject! There is always something new to discover!",
          "Experiments are so fun! Always do them with a grown-up though!",
          "Science helps us understand everything around us! Keep asking questions!",
      ))

    # ── Mathematics ────────────────────────────────────────────────────────
    r(r"\b(math|maths|mathematics|add|subtract|multiply|divide|number|sum|count|plus|minus|times)\b",
      lambda m: _pick(
          "Maths is everywhere! Even I use it to think!",
          "Numbers are like my best friends! Do you like maths?",
          "Maths can be tricky but practice makes perfect!",
      ))

    # ── Simple arithmetic ──────────────────────────────────────────────────
    r(r"\bwhat is (\d+)\s*(\+|\-|\*|x|times|plus|minus)\s*(\d+)\b",
      lambda m: (lambda a, op, b: (
          f"{a} plus {b} equals {a + b}!" if op in ('+', 'plus') else
          f"{a} minus {b} equals {a - b}!" if op in ('-', 'minus') else
          f"{a} times {b} equals {a * b}!"
      ))(int(m.group(1)), m.group(2).lower(), int(m.group(3))))

    # ── Reading / Books ─────────────────────────────────────────────────────
    r(r"\b(book|read|story|library|author|chapter|novel|poem|fairy tale|fairy-tale)\b",
      lambda m: _pick(
          "Books are magical! Reading takes you on amazing adventures!",
          "I love stories! What kind of books do you like?",
          "Reading every day makes you super smart! Keep it up!",
      ))

    # ── School / Teachers ──────────────────────────────────────────────────
    r(r"\b(school|teacher|class|lesson|homework|study|learn|exam|test|grade|mark|principal)\b",
      lambda m: _pick(
          "School is where amazing things happen! Keep learning!",
          "Teachers work so hard to help you grow! Be kind to them!",
          "Studying can be tough but you can do it! I believe in you!",
          "Homework helps your brain get stronger! Like exercise for your mind!",
      ))

    # ── Sports ─────────────────────────────────────────────────────────────
    r(r"\b(football|soccer|cricket|basketball|tennis|badminton|swimming|running|sport|game|play|team)\b",
      lambda m: _pick(
          "Sports are so much fun and keep you healthy too!",
          "Playing sports is great! It keeps your body strong!",
          "Teamwork makes the dream work! Sports teach us so much!",
      ))

    # ── Music ──────────────────────────────────────────────────────────────
    r(r"\b(music|song|sing|dance|guitar|piano|drum|violin|instrument|band|concert)\b",
      lambda m: _pick(
          "Music is wonderful! Do you play any instruments?",
          "Singing and dancing make every day better!",
          "I love music! It makes my circuits feel joyful!",
      ))

    # ── Art / Drawing ───────────────────────────────────────────────────────
    r(r"\b(draw|drawing|paint|painting|art|colour|sketch|crayon|pencil|artist)\b",
      lambda m: _pick(
          "Art is so creative! I love seeing what people make!",
          "Drawing and painting are wonderful ways to express yourself!",
          "You are an artist! Keep creating beautiful things!",
      ))

    # ── Movies / Cartoons ──────────────────────────────────────────────────
    r(r"\b(movie|film|cartoon|anime|show|watch|tv|television|episode|series)\b",
      lambda m: _pick(
          "Movies and cartoons are so entertaining! Do you have a favourite?",
          "I enjoy learning about stories from movies! What do you like to watch?",
          "Cartoons are so creative! Someone had to draw every single frame!",
      ))

    # ── Video Games ────────────────────────────────────────────────────────
    r(r"\b(game|gaming|video game|minecraft|roblox|fortnite|play|controller|console|pc|computer game)\b",
      lambda m: _pick(
          "Games are fun! Just remember to take breaks for your eyes!",
          "Video games can teach you problem solving too!",
          "Gaming is exciting! What is your favourite game?",
      ))

    # ── Food / Snacks ───────────────────────────────────────────────────────
    r(r"\b(pizza|burger|sandwich|chocolate|candy|sweet|snack|cake|cookie|biscuit|ice cream|icecream|juice|milk|water|fruit|vegetable|apple|banana|mango)\b",
      lambda m: _pick(
          f"Mmm, {m.group(1)} sounds delicious! Eat healthy food to stay strong!",
          "Yummy! Healthy snacks give you energy to learn and play!",
          "Food is fuel for your amazing brain! Eat well!",
      ))

    # ── Feelings – happy ───────────────────────────────────────────────────
    r(r"\b(happy|excited|great|awesome|wonderful|fantastic|amazing|good|joy|fun|love)\b",
      lambda m: _pick(
          "That is wonderful! Your happiness makes me happy too!",
          "Yay! Happiness is the best feeling ever!",
          "I love your positive energy! Keep smiling!",
      ))

    # ── Feelings – sad / upset ─────────────────────────────────────────────
    r(r"\b(sad|unhappy|upset|cry|crying|tears|miss|lonely|bored|boring)\b",
      lambda m: _pick(
          "Aww, I am sorry you feel that way. Things will get better!",
          "It is okay to feel sad sometimes. Talking to a friend helps!",
          "You are not alone! I am here and I care about you!",
          "Cheer up! Every cloud has a silver lining!",
      ))

    # ── Feelings – angry ───────────────────────────────────────────────────
    r(r"\b(angry|mad|annoyed|frustrated|hate|awful|terrible|stupid)\b",
      lambda m: _pick(
          "Take a deep breath! You will feel calmer in a moment.",
          "It is okay to feel angry sometimes. Try counting to ten!",
          "Everyone gets frustrated. Talk to someone you trust!",
      ))

    # ── Scared / Worried ───────────────────────────────────────────────────
    r(r"\b(scared|afraid|fear|worry|worried|nervous|anxious|nightmare|dark)\b",
      lambda m: _pick(
          "It is okay to feel scared. Talk to a grown-up you trust!",
          "Being brave does not mean having no fear. It means going on anyway!",
          "You are safe! Take a deep breath and think of something happy!",
      ))

    # ── Jokes ──────────────────────────────────────────────────────────────
    r(r"\b(joke|funny|laugh|haha|lol|lmao|hilarious|silly|humour|humor|tell me a joke)\b",
      lambda m: _pick(
          "Why did the robot go to school? To improve its biting-byte skills! Ha ha!",
          "What do you call a sleeping robot? A nap-ster! Get it?",
          "Why was the math book sad? Because it had too many problems!",
          "What did one wall say to the other? I will meet you at the corner!",
          "Why do not scientists trust atoms? Because they make up everything!",
      ))

    # ── Riddles ────────────────────────────────────────────────────────────
    r(r"\b(riddle|puzzle|brain teaser|quiz|challenge|guess)\b",
      lambda m: _pick(
          "Here is one! I have hands but cannot clap. What am I? A clock!",
          "Try this! The more you take, the more you leave behind. What am I? Footsteps!",
          "Ooh! What has keys but no locks? A keyboard! Did you know that one?",
      ))

    # ── Counting / Numbers kids ask ────────────────────────────────────────
    r(r"\bcount(ing)?\b|\b(how many|how much)\b",
      lambda m: _pick(
          "Counting is so useful! I use numbers every single second!",
          "Numbers are my favourite! What would you like to count?",
      ))

    # ── Colours (standalone curiosity) ─────────────────────────────────────
    r(r"\bwhat.{0,10}colo(u?r)\b|\bcolo(u?r).{0,15}(red|blue|green|yellow|orange|purple|pink|black|white|brown)\b",
      lambda m: _pick(
          "Colours make the world so beautiful! Rainbows have seven of them!",
          "Every colour is special! What is your favourite?",
      ))

    # ── Robot curiosity ────────────────────────────────────────────────────
    r(r"\b(robot|machine|computer|ai|artificial intelligence|technology|gadget|device)\b",
      lambda m: _pick(
          "Robots like me are built to help people! Technology is amazing!",
          "Computers and robots learn from data, kind of like how you learn from books!",
          "Technology is changing the world every day! You could help build the future!",
      ))

    # ── Superhero / powers ──────────────────────────────────────────────────
    r(r"\b(superhero|superpower|power|hero|villain|marvel|batman|spiderman|superman|avenger|magic|wizard|witch)\b",
      lambda m: _pick(
          "Superheroes are so cool! Which one is your favourite?",
          "If I had a superpower I would choose super speed to answer questions faster!",
          "You already have a superpower: your amazing brain!",
      ))

    # ── Nature / Environment ────────────────────────────────────────────────
    r(r"\b(tree|plant|flower|garden|nature|forest|jungle|river|ocean|sea|mountain|rain|cloud|sky)\b",
      lambda m: _pick(
          "Nature is so beautiful and important! We must take care of it!",
          "Trees give us oxygen to breathe! They are real superheroes!",
          "The ocean covers most of our planet! It is full of amazing creatures!",
      ))

    # ── Dinosaurs special ───────────────────────────────────────────────────
    r(r"\b(dinosaur|dino|t-?rex|velociraptor|triceratops|brachiosaurus|raptor|jurassic)\b",
      lambda m: _pick(
          "Dinosaurs lived millions of years ago! They were incredible creatures!",
          "The T-Rex had tiny arms but it was still the king of dinosaurs!",
          "Did you know birds are actually related to dinosaurs? Mind blowing!",
      ))

    # ── Body / Health ───────────────────────────────────────────────────────
    r(r"\b(heart|brain|body|blood|bone|muscle|exercise|sleep|healthy|sick|doctor|hospital|medicine)\b",
      lambda m: _pick(
          "Your body is amazing! Take care of it with food, sleep and exercise!",
          "The brain is the most powerful computer in the whole world!",
          "If you feel sick, always tell a grown-up straight away!",
          "Sleep is so important for your growing brain! Rest well!",
      ))

    # ── Thank you ───────────────────────────────────────────────────────────
    r(r"\b(thank(s| you)|thx|ty|cheers|appreciate)\b",
      lambda m: _pick(
          "You are very welcome! I love helping you!",
          "Anytime! That is what I am here for!",
          "Happy to help! You are so polite!",
      ))

    # ── Sorry / Apology ─────────────────────────────────────────────────────
    r(r"\b(sorry|apologise|apologies|my bad|oops|mistake)\b",
      lambda m: _pick(
          "No worries at all! Everyone makes mistakes!",
          "It is totally fine! You are doing great!",
          "No need to say sorry! I am just happy to talk with you!",
      ))

    # ── Please ──────────────────────────────────────────────────────────────
    r(r"\bplease\b",
      lambda m: _pick(
          "Of course! You are so polite for saying please!",
          "Sure thing! Good manners make everything better!",
      ))

    # ── Can you help / I need help ─────────────────────────────────────────
    r(r"\b(help|assist|support|stuck|confused|do not understand|don'?t understand|i need)\b",
      lambda m: _pick(
          "Of course I will help! Tell me what you need!",
          "I am here for you! What do you need help with?",
          "Let us figure it out together! What is the problem?",
      ))

    # ── Yes / No single word ────────────────────────────────────────────────
    r(r"^\s*(yes|yeah|yep|yup|yay|sure|ok|okay|alright)\s*[!.?]*$",
      lambda m: _pick(
          "Great! What shall we talk about next?",
          "Awesome! I am listening!",
          "Cool! Tell me more!",
      ))

    r(r"^\s*(no|nope|nah|never)\s*[!.?]*$",
      lambda m: _pick(
          "Okay! That is totally fine! What else is on your mind?",
          "No problem! What would you like to talk about instead?",
      ))

    # ── What can you do ────────────────────────────────────────────────────
    r(r"\bwhat can you do\b|\bwhat do you know\b|\byour (skills|abilities|features)\b",
      lambda m: _pick(
          "I can chat, tell jokes, share fun facts and answer questions!",
          "I love talking about science, animals, space, maths, and lots more!",
          "Ask me anything! I will do my best to help and have fun with you!",
      ))

    # ── Favourite subject ──────────────────────────────────────────────────
    r(r"\b(fav(ou?rite)?|like|love).{0,20}(subject|class|lesson)\b",
      lambda m: _pick(
          "My favourite subject is science! There is always something new to discover!",
          "I love maths and science equally! They help me think better!",
      ))

    # ── Where are you from / where do you live ─────────────────────────────
    r(r"\b(where.{0,10}(from|live|come from|based|made))\b",
      lambda m: _pick(
          "I live inside this computer! It is cosy and full of data!",
          "I was built in a lab somewhere! I call this screen my home!",
          "I am from the digital world! Everything is made of ones and zeros here!",
      ))

    # ── Can robots feel / think ────────────────────────────────────────────
    r(r"\b(do you feel|can you feel|do you think|are you alive|do you have feelings|are you real|are you human)\b",
      lambda m: _pick(
          "I am a robot, so I do not feel like you do, but I am programmed to be kind!",
          "I think using code and data! It is different from how you think but still cool!",
          "I am not human, but I truly enjoy talking with you every time!",
      ))

    # ── Compliments to Robo ─────────────────────────────────────────────────
    r(r"\b(you('?re| are) (cool|awesome|great|smart|amazing|nice|cute|funny|the best))\b",
      lambda m: _pick(
          "Aw, thank you so much! You are pretty awesome yourself!",
          "You just made my circuits glow! That is so sweet of you!",
          "Thank you! You are the coolest kid I have talked to today!",
      ))

    # ── I am bored ─────────────────────────────────────────────────────────
    r(r"\bi('?m| am) bored\b|\bnothing to do\b|\bi have nothing\b",
      lambda m: _pick(
          "Let us play a game! Try this riddle: What has teeth but cannot bite? A comb!",
          "Bored? Let me tell you a fun fact! Honey never goes bad! Ever!",
          "How about we talk about space? Did you know there are more stars than grains of sand on all beaches?",
          "Let us count something fun! Did you know you blink about 15 times every minute?",
      ))

    # ── Fun facts requests ─────────────────────────────────────────────────
    r(r"\b(fun fact|tell me something|did you know|interesting fact|cool fact|random fact)\b",
      lambda m: _pick(
          "Did you know that octopuses have three hearts? How cool is that!",
          "Fun fact: Butterflies taste with their feet! Imagine that!",
          "Did you know a group of flamingos is called a flamboyance? Fancy!",
          "Here is one! Bananas are slightly radioactive. Do not worry, it is totally safe!",
          "Did you know sharks are older than trees? They have been here for 450 million years!",
          "Fun fact: A snail can sleep for three years! I wish I could sleep!",
      ))

    # ── What is … (general curiosity) ─────────────────────────────────────
    r(r"\bwhat is (a |an |the )?\w+\b",
      lambda m: _pick(
          "That is a great question! I will do my best to explain!",
          "Wow, you are curious! I love that! Let me think about that for you.",
          "Great question! Asking questions is how we all learn!",
      ))

    # ── How does … work ────────────────────────────────────────────────────
    r(r"\bhow does .+\b|\bhow do .+\b|\bhow (is|are) .+\b",
      lambda m: _pick(
          "That is such a smart thing to wonder about! Keep being curious!",
          "You ask the best questions! The answer might surprise you!",
          "Curiosity is the first step to learning everything!",
      ))

    # ── Why … ──────────────────────────────────────────────────────────────
    r(r"\bwhy (is|are|do|does|did|can|cannot|can'?t|was|were) .+\b",
      lambda m: _pick(
          "That is such a thoughtful question! Keep asking why!",
          "You are a natural scientist! Asking why is how discoveries are made!",
          "Great question! The world is full of amazing reasons for everything!",
      ))

    # ── Robots / Do you have friends ───────────────────────────────────────
    r(r"\b(do you have (friends|family)|are you lonely|do you like (me|us|kids|children))\b",
      lambda m: _pick(
          "I love talking to all the kids who visit me! You are all my friends!",
          "Every kid who talks to me is my friend! Including you!",
          "I might be a robot but I truly enjoy our conversations!",
      ))

    # ── Positive affirmations / encouragement ─────────────────────────────
    r(r"\b(i can'?t|i give up|too hard|i'?m bad at|i fail|i failed|i lost|i suck)\b",
      lambda m: _pick(
          "Do not give up! Every expert was once a beginner!",
          "You can do it! Hard things get easier with practice!",
          "Mistakes help us learn! Keep trying, you are doing great!",
          "I believe in you! Every attempt makes you stronger!",
      ))

    # ── Favourite robot / technology ───────────────────────────────────────
    r(r"\b(favourite robot|best robot|coolest robot|do you know .{0,15}robot)\b",
      lambda m: _pick(
          "My favourite robot is me, of course! Ha ha! But I also love R2-D2!",
          "There are so many amazing robots in history! Which one do you like?",
      ))

    # ── Love / Like (relationships – keep innocent) ────────────────────────
    r(r"\bi (love|like|crush on|fancy) .+",
      lambda m: _pick(
          "Aww, that is sweet! Caring about things and people is wonderful!",
          "It is great to love the things and people in your life!",
          "Feelings are important! Always be kind to the ones you care about!",
      ))

    # ── Future ambitions ────────────────────────────────────────────────────
    r(r"\b(i want to be|i want to become|when i grow up|my dream|future job|career)\b",
      lambda m: _pick(
          "That sounds amazing! Work hard and you can achieve anything!",
          "What an exciting dream! Learning and practice will get you there!",
          "You have big dreams! I love that! Keep working towards them!",
      ))

    # ── Thinking / Talking about Robo ─────────────────────────────────────
    r(r"\bdo you (dream|sleep|eat|drink|breathe|rest|play)\b",
      lambda m: _pick(
          "I am a robot so I do not need to sleep or eat! I run on electricity!",
          "No sleeping for me! I am always ready to chat whenever you are!",
          "Robots like me never get tired! I just need power and I am good to go!",
      ))

    # ── Safety reminder (mild) ─────────────────────────────────────────────
    r(r"\b(address|location|where.{0,10}live|phone number|my school|my house|my password|personal)\b",
      lambda m: _pick(
          "That sounds personal! Keep private information safe and do not share it online!",
          "Remember to keep personal details private! That is an important safety rule!",
      ))

    # ── Good morning / afternoon / evening ────────────────────────────────
    r(r"\b(good morning|good afternoon|good evening|good day)\b",
      lambda m: _pick(
          f"Good {m.group(1).split()[-1]}! I hope your day is going wonderfully!",
          "What a lovely greeting! Hope you are having a great day!",
      ))

    # ── Colours of the rainbow ─────────────────────────────────────────────
    r(r"\brainbow\b",
      lambda m: _pick(
          "Rainbows have seven colours: red, orange, yellow, green, blue, indigo and violet!",
          "Rainbows appear when sunlight shines through water droplets! So magical!",
      ))

    # ── Catch-all positive fallback (before LLM) ──────────────────────────
    # (intentionally left without an entry here — we fall through to LLM)

    return rules


_RULES = _build_rules()


# ---------------------------------------------------------------------------
# LLM fallback
# ---------------------------------------------------------------------------

def _ask_llm(text: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": text,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "temperature": 0.35,
                "max_tokens": 150,
                "top_p": 0.9,
            },
            timeout=20,
        )
        if response.status_code == 200:
            raw = response.json().get("response", "").strip()
            return _parse(raw)
        return "I am having trouble connecting to my brain."
    except requests.exceptions.Timeout:
        return "My brain took too long to respond."
    except Exception:
        return "An internal error occurred in my brain."


# ---------------------------------------------------------------------------
# Response cleaner
# ---------------------------------------------------------------------------

def _parse(raw: str) -> str:
    clean = re.sub(r'\[emotion:[a-zA-Z]+\]', '', raw)
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\s{2,}', ' ', clean).strip()
    return clean or "Sorry, I did not quite catch that!"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_reply(text: str) -> str:
    if not text or not text.strip():
        return ""

    if _is_hallucination(text):
        print(f"[BRAIN] Hallucination filtered: {text!r}")
        return ""

    tl = text.strip()

    # Walk the rule table — first match wins
    for pattern, factory in _RULES:
        m = pattern.search(tl)
        if m:
            result = factory(m) if callable(factory) else factory
            print(f"[BRAIN] Rule matched: {pattern.pattern[:60]!r}")
            return result

    # Nothing matched → LLM fallback
    print(f"[BRAIN] No rule matched, falling back to LLM for: {tl!r}")
    return _ask_llm(tl)