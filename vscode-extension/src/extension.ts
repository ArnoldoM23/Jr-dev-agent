import * as vscode from 'vscode';
import { JrDevParticipant } from './participants/jrDevParticipant';

// This method is called when your extension is activated
export function activate(context: vscode.ExtensionContext) {
    console.log('🚀 Jr Dev Agent extension is now active!');

    // Create output channel for logging
    const outputChannel = vscode.window.createOutputChannel('Jr Dev Agent');
    
    // Create and register the Jr Dev chat participant
    const jrDevParticipant = new JrDevParticipant(context, outputChannel);
    const participantDisposable = jrDevParticipant.register();

    // Register disposables
    context.subscriptions.push(participantDisposable);
    context.subscriptions.push(outputChannel);

    // Register follow-up commands for the chat participant
    const markCompleteCommand = vscode.commands.registerCommand('jr-dev.markComplete', async () => {
        const currentSession = jrDevParticipant.getCurrentSession();
        if (!currentSession) {
            vscode.window.showErrorMessage('No active Jr Dev session to mark complete');
            return;
        }

        const prUrl = await vscode.window.showInputBox({
            prompt: 'Enter the PR URL (optional)',
            placeHolder: 'https://github.com/org/repo/pull/123'
        });

        try {
            await jrDevParticipant.markSessionComplete(prUrl);
            vscode.window.showInformationMessage(
                `✅ Session ${currentSession.ticketId} marked complete! Thanks for the feedback.`
            );
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to mark session complete: ${error}`);
        }
    });

    const showSessionDetailsCommand = vscode.commands.registerCommand('jr-dev.showSessionDetails', () => {
        const currentSession = jrDevParticipant.getCurrentSession();
        if (!currentSession) {
            vscode.window.showErrorMessage('No active Jr Dev session');
            return;
        }

        const details = `
📋 Session Details:
• Session ID: ${currentSession.sessionId}
• Ticket ID: ${currentSession.ticketId}
• Status: ${currentSession.status}
• Started: ${currentSession.startTime.toLocaleString()}
• Prompt Hash: ${currentSession.promptHash || 'N/A'}
        `;

        vscode.window.showInformationMessage(details);
    });

    // Register the follow-up commands
    context.subscriptions.push(markCompleteCommand);
    context.subscriptions.push(showSessionDetailsCommand);

    // Show activation message
    vscode.window.showInformationMessage(
        '🚀 Jr Dev Agent is ready! Use @jrdev TICKET-ID in VS Code Chat to get started.'
    );
    
    outputChannel.appendLine('Jr Dev Agent extension activated successfully');
    outputChannel.appendLine('Usage: Type @jrdev TICKET-ID in VS Code Chat');
}

// This method is called when your extension is deactivated
export function deactivate() {
    console.log('👋 Jr Dev Agent extension is deactivated');
} 