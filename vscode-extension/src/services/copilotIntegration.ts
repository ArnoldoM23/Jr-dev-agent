import * as vscode from 'vscode';

export class CopilotIntegration {
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('Jr Dev Agent');
    }

    /**
     * Sends a prompt to VS Code Chat by creating a new chat session
     * This simulates the user typing the prompt directly into chat
     */
    async sendPromptToCopilot(prompt: string): Promise<void> {
        try {
            this.outputChannel.appendLine(`Sending prompt to Copilot Chat. Length: ${prompt.length}`);
            
            // Focus the chat panel first
            await vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
            
            // Small delay to ensure chat panel is ready
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Create a new chat session with the prompt
            // This opens a new chat conversation with the generated prompt
            await vscode.commands.executeCommand('workbench.action.chat.newChat');
            
            // Send the prompt to the chat
            await vscode.commands.executeCommand('workbench.action.chat.sendToNewChat', {
                message: prompt
            });
            
            this.outputChannel.appendLine('✅ Prompt sent to Copilot Chat successfully');
            
        } catch (error) {
            this.outputChannel.appendLine(`❌ Error sending prompt to Copilot: ${error}`);
            
            // Fallback: Show the prompt in a text document
            await this.showPromptInTextDocument(prompt);
            
            throw new Error(`Failed to send prompt to Copilot Chat: ${error}`);
        }
    }

    /**
     * Fallback method to show the prompt in a new text document
     * This is used when direct chat integration fails
     */
    private async showPromptInTextDocument(prompt: string): Promise<void> {
        try {
            const document = await vscode.workspace.openTextDocument({
                content: prompt,
                language: 'markdown'
            });
            
            await vscode.window.showTextDocument(document);
            
            vscode.window.showInformationMessage(
                '📋 Prompt generated! Copy this content and paste it into Copilot Chat manually.',
                'Open Copilot Chat'
            ).then(selection => {
                if (selection === 'Open Copilot Chat') {
                    vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
                }
            });
            
        } catch (error) {
            this.outputChannel.appendLine(`❌ Error showing prompt in text document: ${error}`);
        }
    }

    /**
     * Test method to check if Copilot Chat is available
     */
    async testCopilotAvailability(): Promise<boolean> {
        try {
            await vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
            return true;
        } catch (error) {
            this.outputChannel.appendLine(`Copilot Chat not available: ${error}`);
            return false;
        }
    }
} 