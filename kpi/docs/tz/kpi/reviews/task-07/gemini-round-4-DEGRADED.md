Error authenticating: FatalAuthenticationError: Manual authorization is required but the current session is non-interactive. Please run the Gemini CLI in an interactive terminal to log in, provide a GEMINI_API_KEY, or ensure Application Default Credentials are configured.
    at initOauthClient (file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/chunk-UIBQS45C.js:250543:13)
    at process.processTicksAndRejections (node:internal/process/task_queues:103:5)
    at async createCodeAssistContentGenerator (file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/chunk-UIBQS45C.js:278491:24)
    at async file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/chunk-UIBQS45C.js:278831:42
    at async createContentGenerator (file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/chunk-UIBQS45C.js:278788:21)
    at async Config.refreshAuth (file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/chunk-UIBQS45C.js:352595:29)
    at async main (file:///home/aiagent/.local/lib/node_modules/@google/gemini-cli/bundle/gemini-JN2NUSDI.js:15034:9) {
  exitCode: 41
}
[31mManual authorization is required but the current session is non-interactive. Please run the Gemini CLI in an interactive terminal to log in, provide a GEMINI_API_KEY, or ensure Application Default Credentials are configured.[0m
