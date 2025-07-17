# Jr Dev Agent - VS Code Extension

AI-powered junior developer agent that converts Jira tickets into working pull requests through VS Code Chat.

## 🚀 Features

- **Chat Participant**: Use `@jrdev TICKET-ID` directly in VS Code Chat
- **Offline Support**: Works without MCP server using fallback data
- **Smart Prompts**: Generates AI-optimized prompts for GitHub Copilot
- **Session Management**: Tracks development sessions for analytics
- **Follow-up Actions**: Mark PRs complete and track feedback

## 📦 Installation

### Development Installation
1. Clone the repository
2. Navigate to the extension directory: `cd vscode-extension`
3. Install dependencies: `npm install`
4. Compile the extension: `npm run compile`
5. Open VS Code and press `F5` to run the extension in a new window

### Production Installation
*Coming soon - will be available on VS Code Marketplace*

## 🎯 Usage

### Basic Usage
1. Open VS Code Chat (View → Chat)
2. Type `@jrdev TICKET-ID` where TICKET-ID is your Jira ticket (e.g., `CEPG-12345`)
3. The extension will:
   - Fetch ticket metadata from Jira (or use fallback data)
   - Generate an AI-optimized prompt
   - Display the prompt in chat
4. Copy the generated prompt and use it with GitHub Copilot

### Examples
```
@jrdev CEPG-12345
@jrdev JIRA-456
@jrdev PROJ-789
```

### Follow-up Actions
After the agent processes your ticket, you can:
- **Mark PR Complete**: Use the follow-up button to mark when your PR is ready
- **View Session Details**: See information about your current session

## ⚙️ Configuration

Configure the extension through VS Code Settings (`Ctrl+,` or `Cmd+,`):

### Settings
- **MCP Server URL**: `http://localhost:8000` (default)
- **API Key**: Your MCP server authentication key
- **Dev Mode**: Enable to use fallback data immediately (good for testing)
- **Timeout**: Request timeout in milliseconds (default: 5000ms)

### Configuration Path
```
Jr Dev Agent Settings → Configure individual settings
```

## 🔧 Development

### Build Commands
- `npm run compile` - Compile TypeScript to JavaScript
- `npm run watch` - Watch for changes and recompile
- `npm run lint` - Run ESLint
- `npm run test` - Run tests

### Architecture
- **Chat Participant**: `src/participants/jrDevParticipant.ts`
- **MCP Client**: `src/services/mcpClient.ts`
- **Copilot Integration**: `src/services/copilotIntegration.ts`
- **Main Extension**: `src/extension.ts`

### Testing
Run the extension in development mode:
1. Press `F5` in VS Code
2. A new Extension Development Host window opens
3. Test the `@jrdev` command in VS Code Chat

## 📝 Error Handling

### Common Issues
- **No ticket ID**: Make sure format is `PROJECT-123` (letters, dash, numbers)
- **MCP server unavailable**: Extension automatically falls back to offline mode
- **Invalid ticket**: Check that the ticket exists in Jira

### Troubleshooting
1. Check the "Jr Dev Agent" output panel for detailed logs
2. Verify your MCP server is running on the configured URL
3. Try enabling dev mode for testing with fallback data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- **LangGraph MCP Server**: The orchestration backend
- **PromptBuilder**: Template generation service
- **PESS**: Prompt effectiveness scoring system
- **Synthetic Memory**: Context enrichment system

---

**Made with ❤️ by the Jr Dev Team** 