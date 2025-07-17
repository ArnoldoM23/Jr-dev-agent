import * as vscode from 'vscode';
import { MCPClient } from '../services/mcpClient';
import { v4 as uuidv4 } from 'uuid';

// Define the participant ID
const JR_DEV_PARTICIPANT_ID = 'jrdev';

interface JrDevSession {
    sessionId: string;
    ticketId: string;
    startTime: Date;
    status: 'in_progress' | 'completed' | 'failed';
    promptGenerated?: string;
    promptHash?: string;
}

/**
 * JrDevParticipant handles chat requests to convert Jira tickets into working code.
 * Users can mention @jrdev TICKET-ID in VS Code Chat to trigger the agent.
 */
export class JrDevParticipant {
    private outputChannel: vscode.OutputChannel;
    private mcpClient: MCPClient;
    private currentSession: JrDevSession | null = null;

    constructor(
        private context: vscode.ExtensionContext,
        outputChannel: vscode.OutputChannel
    ) {
        this.outputChannel = outputChannel;
        this.mcpClient = new MCPClient(context);
        this.outputChannel.appendLine('JrDevParticipant initialized.');
    }

    /**
     * Registers the participant with the VS Code Chat API
     */
    public register(): vscode.Disposable {
        this.outputChannel.appendLine('Registering Jr Dev chat participant...');
        
        try {
            const requestHandler: vscode.ChatRequestHandler = this.createRequestHandler();
            const participant = vscode.chat.createChatParticipant(JR_DEV_PARTICIPANT_ID, requestHandler);
            participant.iconPath = new vscode.ThemeIcon('robot');
            participant.followupProvider = {
                provideFollowups(result: vscode.ChatResult, context: vscode.ChatContext, token: vscode.CancellationToken) {
                    if (result.metadata?.ticketId) {
                        return [
                            { prompt: `Mark PR complete for ${result.metadata.ticketId}`, label: 'Mark PR Complete' },
                            { prompt: `Show session details for ${result.metadata.ticketId}`, label: 'Session Details' }
                        ];
                    }
                    return [];
                }
            };
            
            this.outputChannel.appendLine('Successfully registered Jr Dev chat participant');
            return participant;
        } catch (error) {
            this.outputChannel.appendLine(`Error registering chat participant: ${error}`);
            vscode.window.showErrorMessage(`Failed to register Jr Dev chat participant: ${error}`);
            return { dispose: () => {} };
        }
    }

    /**
     * Creates a request handler function for the chat participant
     */
    private createRequestHandler(): vscode.ChatRequestHandler {
        return async (
            request: vscode.ChatRequest,
            context: vscode.ChatContext,
            response: vscode.ChatResponseStream,
            token: vscode.CancellationToken
        ): Promise<vscode.ChatResult> => {
            this.outputChannel.appendLine(`Received Jr Dev request: ${request.prompt.substring(0, 100)}...`);

            try {
                // Extract ticket ID from the prompt
                const ticketId = this.extractTicketIdFromPrompt(request.prompt);
                
                if (!ticketId) {
                    response.markdown(`🔴 **Error:** No valid ticket ID found in your request.

**Usage:** Type \`@jrdev TICKET-ID\` where TICKET-ID follows the format PROJECT-123

**Examples:**
- \`@jrdev CEPG-12345\`
- \`@jrdev JIRA-456\`
- \`@jrdev PROJ-789\`

**Valid Format:** Letters followed by dash and numbers (e.g., ABC-123)`);
                    return { metadata: { error: 'No ticket ID provided' } };
                }

                if (token.isCancellationRequested) {
                    response.markdown("Operation cancelled by user.");
                    return {};
                }

                // Start new session
                this.startNewSession(ticketId);
                response.markdown(`🚀 **Jr Dev Agent Started**\n\n📋 Processing ticket: \`${ticketId}\`\n\n---\n\n`);

                // Step 1: Fetch ticket metadata
                response.progress('Fetching ticket metadata...');
                const ticketData = await this.mcpClient.getTicketMetadata(ticketId);
                
                if (token.isCancellationRequested) {
                    response.markdown("Operation cancelled by user.");
                    return {};
                }

                // Show ticket information
                response.markdown(`✅ **Ticket Information Retrieved**\n\n`);
                response.markdown(`**Summary:** ${ticketData.summary}\n\n`);
                response.markdown(`**Priority:** ${ticketData.priority} | **Feature:** ${ticketData.feature}\n\n`);
                if (ticketData.source === 'fallback') {
                    response.markdown(`⚠️ *Using offline mode (MCP server unavailable)*\n\n`);
                }

                // Step 2: Generate prompt
                response.progress('Generating AI prompt...');
                const promptData = await this.mcpClient.generatePrompt(ticketData);
                
                if (token.isCancellationRequested) {
                    response.markdown("Operation cancelled by user.");
                    return {};
                }

                // Update session
                if (this.currentSession) {
                    this.currentSession.promptGenerated = promptData.prompt;
                    this.currentSession.promptHash = promptData.hash;
                    this.currentSession.status = 'completed';
                }

                // Step 3: Display the generated prompt
                response.markdown(`✅ **AI Prompt Generated**\n\n`);
                response.markdown(`**Template Used:** ${promptData.template_used}\n\n`);
                response.markdown(`**Generated Prompt:**\n\n---\n\n${promptData.prompt}\n\n---\n\n`);

                // Step 4: Show completion options
                response.markdown(`🎯 **Next Steps:**\n\n`);
                response.markdown(`1. **Copy the prompt above** and paste it into a new Copilot Chat session\n`);
                response.markdown(`2. **Let Copilot generate the code** based on the prompt\n`);
                response.markdown(`3. **Review and implement** the generated code\n`);
                response.markdown(`4. **Create a pull request** with your changes\n`);
                response.markdown(`5. **Mark the session complete** using the follow-up buttons\n\n`);

                response.markdown(`💡 **Pro Tip:** Use the "Mark PR Complete" follow-up to help improve the system!`);

                this.outputChannel.appendLine('Jr Dev request processed successfully');
                return { 
                    metadata: { 
                        ticketId,
                        sessionId: this.currentSession?.sessionId,
                        promptHash: promptData.hash,
                        templateUsed: promptData.template_used
                    } 
                };

            } catch (error) {
                this.outputChannel.appendLine(`Error in Jr Dev request handler: ${error}`);
                
                if (this.currentSession) {
                    this.currentSession.status = 'failed';
                }

                const errorMessage = error instanceof Error ? error.message : String(error);
                response.markdown(`🔴 **Jr Dev Agent Error**\n\nSomething went wrong while processing your request:\n\n\`\`\`\n${errorMessage}\n\`\`\`\n\n**Troubleshooting:**\n- Check if the ticket ID format is correct (PROJECT-123)\n- Verify MCP server is running (or use dev mode)\n- Check the Jr Dev Agent output panel for details`);
                
                return { metadata: { error: errorMessage } };
            }
        };
    }

    /**
     * Extract ticket ID from the chat prompt
     */
    private extractTicketIdFromPrompt(prompt: string): string | null {
        // Remove @jrdev mention and clean up
        const cleanPrompt = prompt.replace(/^@jrdev\s*/i, '').trim();
        
        // Match ticket ID pattern: LETTERS-NUMBERS (e.g., CEPG-12345)
        const ticketPattern = /^([A-Z]+-\d+)/;
        const match = cleanPrompt.match(ticketPattern);
        
        return match ? match[1] : null;
    }

    /**
     * Start a new Jr Dev session
     */
    private startNewSession(ticketId: string): void {
        this.currentSession = {
            sessionId: `jr_dev_${ticketId}_${uuidv4()}`,
            ticketId,
            startTime: new Date(),
            status: 'in_progress'
        };
        this.outputChannel.appendLine(`Started new Jr Dev session: ${this.currentSession.sessionId}`);
    }

    /**
     * Mark the current session as complete
     */
    async markSessionComplete(prUrl?: string): Promise<void> {
        if (!this.currentSession) {
            throw new Error('No active session to mark complete');
        }

        try {
            await this.mcpClient.markSessionComplete(this.currentSession.sessionId, prUrl);
            this.outputChannel.appendLine(`Session ${this.currentSession.sessionId} marked complete`);
            this.currentSession = null;
        } catch (error) {
            this.outputChannel.appendLine(`Error marking session complete: ${error}`);
            throw error;
        }
    }

    /**
     * Get current session details
     */
    getCurrentSession(): JrDevSession | null {
        return this.currentSession;
    }
} 