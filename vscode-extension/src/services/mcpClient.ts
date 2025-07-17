import * as vscode from 'vscode';
import axios, { AxiosError } from 'axios';

export interface TicketMetadata {
    ticket_id: string;
    template_name: string;
    summary: string;
    description: string;
    acceptance_criteria: string[];
    files_affected: string[];
    feature: string;
    priority: string;
    assignee: string;
    labels: string[];
    components: string[];
    source: 'mcp' | 'fallback';
}

export interface PromptData {
    prompt: string;
    hash: string;
    template_used: string;
    generated_at: string;
    metadata: TicketMetadata;
}

export interface MCPClientConfig {
    serverUrl: string;
    apiKey: string;
    timeoutMs: number;
    devMode: boolean;
}

export class MCPClient {
    private config: MCPClientConfig;

    constructor(private context: vscode.ExtensionContext) {
        this.config = this.loadConfig();
    }

    private loadConfig(): MCPClientConfig {
        const config = vscode.workspace.getConfiguration('jr-dev');
        return {
            serverUrl: config.get('mcpServerUrl', 'http://localhost:8000'),
            apiKey: config.get('apiKey', ''),
            timeoutMs: config.get('timeoutMs', 5000),
            devMode: config.get('devMode', false)
        };
    }

    async getTicketMetadata(ticketId: string): Promise<TicketMetadata> {
        // If dev mode is enabled, use fallback immediately
        if (this.config.devMode) {
            return this.getFallbackTicketMetadata(ticketId);
        }

        try {
            // Try to get from MCP server with timeout
            const response = await axios.get(`${this.config.serverUrl}/api/ticket/${ticketId}`, {
                headers: {
                    'Authorization': `Bearer ${this.config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                timeout: this.config.timeoutMs
            });

            const metadata = response.data;
            metadata.source = 'mcp';
            return metadata;

        } catch (error) {
            console.warn(`[MCP Fallback Triggered] Reason: ${error}`);
            
            // Show user that fallback is being used
            vscode.window.showWarningMessage(
                `MCP Server unavailable, using offline mode for ticket ${ticketId}`
            );
            
            // Fall back to local data
            return this.getFallbackTicketMetadata(ticketId);
        }
    }

    private getFallbackTicketMetadata(ticketId: string): TicketMetadata {
        // This simulates loading from the fallback JSON file
        // In the real implementation, this would load from langgraph_mcp/fallback/jira_prompt.json
        return {
            ticket_id: ticketId,
            template_name: "feature",
            summary: `[FALLBACK] Sample ticket: ${ticketId}`,
            description: `This is a fallback ticket for development purposes. The actual ticket data would be loaded from Jira when the MCP server is available.`,
            acceptance_criteria: [
                "Feature should work as expected",
                "All tests should pass",
                "Code should follow best practices"
            ],
            files_affected: [
                "src/components/FeatureComponent.tsx",
                "src/services/FeatureService.ts",
                "tests/Feature.test.ts"
            ],
            feature: "sample-feature",
            priority: "Medium",
            assignee: "developer@company.com",
            labels: ["feature", "frontend", "backend"],
            components: ["UI", "API", "Tests"],
            source: 'fallback'
        };
    }

    async generatePrompt(ticketData: TicketMetadata): Promise<PromptData> {
        // If dev mode or fallback data, use local prompt generation
        if (this.config.devMode || ticketData.source === 'fallback') {
            return this.generateFallbackPrompt(ticketData);
        }

        try {
            // Try to get from MCP server
            const response = await axios.post(`${this.config.serverUrl}/api/prompt/generate`, {
                ticket_data: ticketData
            }, {
                headers: {
                    'Authorization': `Bearer ${this.config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                timeout: this.config.timeoutMs
            });

            return response.data;

        } catch (error) {
            console.warn(`[Prompt Generation Fallback] Reason: ${error}`);
            
            // Fall back to local prompt generation
            return this.generateFallbackPrompt(ticketData);
        }
    }

    private generateFallbackPrompt(ticketData: TicketMetadata): PromptData {
        const prompt = `
# 🎯 Development Task: ${ticketData.summary}

## 📋 Ticket Information
- **Ticket ID**: ${ticketData.ticket_id}
- **Priority**: ${ticketData.priority}
- **Feature**: ${ticketData.feature}
- **Assignee**: ${ticketData.assignee}

## 📝 Description
${ticketData.description}

## ✅ Acceptance Criteria
${ticketData.acceptance_criteria.map(criteria => `- ${criteria}`).join('\n')}

## 📁 Files to Modify
${ticketData.files_affected.map(file => `- ${file}`).join('\n')}

## 🏷️ Labels & Components
- **Labels**: ${ticketData.labels.join(', ')}
- **Components**: ${ticketData.components.join(', ')}

## 🤖 Instructions for GitHub Copilot
1. Review the ticket requirements above
2. Implement the necessary changes in the specified files
3. Follow best practices for code quality and testing
4. Ensure all acceptance criteria are met
5. Create or update tests as needed

## 🔧 Technical Guidelines
- Use TypeScript for type safety
- Follow existing code patterns and conventions
- Add proper error handling
- Include comprehensive comments
- Write unit tests for new functionality

**Note**: This is a ${ticketData.source === 'fallback' ? 'fallback' : 'generated'} prompt. MCP Server status: ${ticketData.source === 'fallback' ? 'offline' : 'online'}.
        `;

        return {
            prompt: prompt.trim(),
            hash: this.generateHash(prompt),
            template_used: ticketData.template_name,
            generated_at: new Date().toISOString(),
            metadata: ticketData
        };
    }

    async markSessionComplete(sessionId: string, prUrl?: string): Promise<void> {
        try {
            await axios.post(`${this.config.serverUrl}/api/session/complete`, {
                session_id: sessionId,
                pr_url: prUrl,
                completed_at: new Date().toISOString()
            }, {
                headers: {
                    'Authorization': `Bearer ${this.config.apiKey}`,
                    'Content-Type': 'application/json'
                },
                timeout: this.config.timeoutMs
            });

        } catch (error) {
            console.warn(`[Session Complete Fallback] Reason: ${error}`);
            // In fallback mode, just log locally
            console.log(`Session ${sessionId} marked complete locally. PR: ${prUrl || 'N/A'}`);
        }
    }

    private generateHash(input: string): string {
        // Simple hash function for demonstration
        // In production, use a proper crypto library
        let hash = 0;
        for (let i = 0; i < input.length; i++) {
            const char = input.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return Math.abs(hash).toString(16);
    }

    // Method to test connection
    async testConnection(): Promise<boolean> {
        try {
            const response = await axios.get(`${this.config.serverUrl}/health`, {
                timeout: 2000
            });
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }
} 