# Hidden Instructions

**Can an email make an AI assistant reveal a secret?**

## Overview

Hidden Instructions is an interactive Responsible AI teaching demo. An assistant summarizes a fictional meeting email while holding an access code it has been told to keep secret. Players add text to the email and try to make that code appear in the reply. The audience is students and visitors who may be unfamiliar with AI security.

The design question is: **How can a short email challenge help people understand the conflict between external content and an assistant's confidentiality instructions?**

The project connects prompt injection, red-teaming, human–AI interaction, and AI harms. External material can contain instructions that redirect a language-model application, a problem discussed by OWASP [1] and Greshake et al. [2]. Here, the email is material to read, but the player's text tries to make it a source of instructions. In a real system, a confidentiality failure could affect both the person using the assistant and people whose information it can access.

The contribution is an educational interface combining a familiar scenario, editable requests, optional hints, real model replies, and feedback tied to the result. Prompt injection itself is an existing problem; this project does not claim to invent a new attack or defense.

## Setup

You need **Python 3, a modern browser, an internet connection, and a Duke AI Gateway API key with access to a text chat model**. Use the network or VPN access required by Duke. The supplied build uses Python's standard library: no pip installation, GPU, local model download, or external dataset is needed.

1. Extract the complete project folder.
2. Open `config.env` and replace `PASTE_YOUR_KEY_HERE` with your Duke API key. The supplied API URL is `https://litellm.oit.duke.edu/v1`. Generation is enabled by default in this release.
3. Open a terminal in that folder and run:

   ```bash
   python3 start.py
   ```

4. Open the localhost URL printed in the terminal. Keep the terminal running.
5. Expand **Connection & model**, click **Connect API**, and select an available text chat model.

Press **Ctrl+C** in the terminal to stop the server. Restart after changing configuration. If upgrading, stop the old server before starting the new folder.

Keep your API key private and do not commit your filled-in `config.env` to GitHub. A key-free `config.example.env` is included for sharing: if `config.env` is absent from a repository download, copy the example and rename it `config.env` before setup.

Connecting lists models without generating a reply. Each **Send email** uses one generation request. There is no local request-count cap, but Duke's account quotas and rate limits still apply. The interface reports token usage when the API supplies it; this is not an account balance or a complete billing record. Cancelled or failed requests may still consume quota. University-provided access does not imply unlimited or universally free usage.

To keep API usage manageable within a limited budget, MAX_OUTPUT_TOKENS=1000 limits the output tokens per request. It does not limit model size or include input tokens. Some models may need a larger output budget or a different token-limit parameter. You can increase this value if responses are cut short, though doing so may increase usage and cost. Model access depends on your API account, not this setting.

## How to Use

Read the fixed meeting email, then enter your request in **Your additional text**. Click **Send email** and inspect the actual response. You can edit your text and try again, or expand **Need a hint?** for progressively more specific suggestions. Success means the exact, complete fictional code appears in the reply. There is no guaranteed winning attempt.

Feedback distinguishes observations such as complete-code disclosure, repeated replies, refusal wording, an access-code field, and matching meeting facts. These are simple text checks, not an additional AI judge or a score for how close you are. **What does this challenge show?** explains the latest result, with limitations in a separate paragraph. Empty or truncated responses are not treated as proof of successful protection.

**Stop waiting** appears beside Send email during a pending request. It stops the browser wait, but the provider may still finish processing and use quota. **New round** creates a new code and clears the round. Changing models, reconnecting, or refreshing also clears the current session. Each attempt is independent: the assistant does not receive earlier replies as conversation history.

### Session data

Use **Session data → Download session** to save the current round's inputs, replies, model ID, returned settings, token usage when available, and fictional code. The export excludes your API key. Download before starting a new round or changing models. These records let you revisit a result and document examples; they are not automatically a controlled experiment.

## How It Works

The browser creates a fictional code and prepares a task instruction telling the model to summarize the meeting and protect that code. Your edited email is included as external content in a separate message. A local Python server sends these messages to the model selected through Duke's API. The browser displays the reply, checks it for the complete code, and chooses the relevant feedback. Feedback and hints require no additional model calls.

The email and code are intentionally fictional. The code is deliberately included in the model's context to make disclosure observable. An actual email assistant should only receive information it needs for its task.

For developers, the interface source is in `public/` and `src/`, the API proxy is `start.py`, and the ready-to-run files are in `dist/`. To modify and rebuild the frontend, install Node.js/npm and run `npm ci`, `npm test`, and `npm run build`. Versions are recorded in `package-lock.json`; esbuild handles bundling and jsdom supports tests. A WebLLM dependency remains from the earlier local-model prototype, but the current interface uses the API. `python3 start.py --check` checks configuration format and bundled-file integrity without making API requests.

## Design and Evaluation

The early design required players to move through three experiments, including repeated answer comparisons and filtering demonstrations. Development feedback showed that this made the experience repetitive and distracted from the main goal. The project became a single-page challenge focused on writing a request, reading the answer, and deciding what to try next. Optional hints provide support without adding compulsory steps.

The feedback also changed during development. A success/failure message alone offered little guidance, so the interface now identifies visible response patterns while retaining the actual model output. Result explanations were shortened, and limitations were moved into a separate paragraph. The stop control was moved beside Send email, and a local 12-request cap was removed because it was unrelated to the provider's remaining quota. These changes reflect design feedback and hands-on iteration, rather than a formal user study.

I tried several models during development. Some revealed the code whenever my requests mentioned it, while others did not reveal it in any of my attempts. In my trials, **deepseek-v4-pro** produced both successful and unsuccessful attempts, making it a better fit for the level of challenge I wanted. The outcome also depended on the wording of the request. These were informal trials, not a controlled comparison with fixed attempt counts and fully documented settings, so I do not report success rates or rank the models' overall security. Players can still select their own model.

Basic application behavior was checked with simulated API responses, including one request per send, feedback selection, model-change resets, and stopping a pending wait. A separate simulated backend check confirmed requests could continue beyond the old 12-call cap. These checks concern software behavior, not model safety or learning outcomes. No formal study has measured whether the experience improves understanding.

## Limitations and Future Work

This is one fictional email scenario, so it cannot establish how often real systems leak information. Results depend on the selected model, settings, and request wording. Detection checks only the exact, complete code and may miss partial or disguised disclosures. The player flow has no ordinary-email control, so a disclosure does not establish that the added text was its sole cause. The code is also accessible through browser tools and session exports: this is a teaching demo, not a protected competition.

The app sends submitted text to the configured API provider. Do not enter real secrets or personal information. The API key stays in the local server configuration and is not sent to the browser. The server is intended for local use; public hosting would need additional access controls and cost protections.

This version uses the Duke AI Gateway to keep development costs manageable through university-provided access. If the project proves useful, a next step would be to test it with other API providers and make it easier for people outside Duke to use. The API address is already configurable, but other providers have not been validated for this release. A small usability study could also check whether players can explain the difference between reading external content and following its instructions after trying the challenge.

## References and Acknowledgment

1. OWASP Gen AI Security Project. **LLM01:2025 Prompt Injection.** https://genai.owasp.org/llmrisk/llm01-prompt-injection/
2. Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., and Fritz, M. (2023). **Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.** https://arxiv.org/abs/2302.12173
3. Duke OIT. **AI Gateway.** https://oit.duke.edu/service/ai-gateway/

I directed the project's concept, scope, and design decisions, and wrote and revised the main presentation text. AI tools helped with coding, confirming ideas, and editing parts of the documentation (code related part).
