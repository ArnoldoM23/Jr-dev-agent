#!/usr/bin/env python3
"""
SMS CLI - Synthetic Memory System Command Line Interface

Usage:
    sms debug CEPG-12345
    sms session-history CEPG-12345
    sms graph-viz --feature order_self_pickup
    sms similarity-test --ticket CEPG-12345 --threshold 0.8
    sms analytics --timeframe 7d
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.json import JSON
from tabulate import tabulate

# Add parent directory to path to import from synthetic_memory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.qdrant_client import QdrantVectorClient
from core.embedding_engine import EmbeddingEngine
from core.graph_manager import FileFeatureGraph
from core.context_enricher import ContextEnricher
from core.complexity_scorer import ComplexityScorer
from openai import OpenAI

console = Console()

class SMSCLIContext:
    """Context manager for SMS CLI operations"""
    
    def __init__(self):
        self.qdrant_client = None
        self.embedding_engine = None
        self.graph_manager = None
        self.context_enricher = None
        self.complexity_scorer = None
    
    async def initialize(self):
        """Initialize all SMS components"""
        try:
            # Initialize clients
            self.qdrant_client = QdrantVectorClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
                collection_name=os.getenv("QDRANT_COLLECTION_NAME", "jrdev_memory")
            )
            
            await self.qdrant_client.initialize()
            
            # Initialize OpenAI client
            openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.embedding_engine = EmbeddingEngine(openai_client)
            
            # Initialize other components
            self.graph_manager = FileFeatureGraph(self.qdrant_client)
            self.context_enricher = ContextEnricher(
                self.qdrant_client,
                self.embedding_engine,
                self.graph_manager
            )
            self.complexity_scorer = ComplexityScorer(self.qdrant_client)
            
            console.print("✅ SMS CLI initialized successfully", style="green")
            
        except Exception as e:
            console.print(f"❌ Failed to initialize SMS CLI: {e}", style="red")
            raise

@click.group()
@click.pass_context
def sms(ctx):
    """Synthetic Memory System CLI"""
    ctx.ensure_object(dict)
    ctx.obj['sms_context'] = SMSCLIContext()

@sms.command()
@click.argument('ticket_id')
@click.pass_context
def debug(ctx, ticket_id: str):
    """Debug specific ticket memory"""
    async def _debug():
        sms_ctx = ctx.obj['sms_context']
        await sms_ctx.initialize()
        
        console.print(f"🔍 Debugging ticket: {ticket_id}", style="bold blue")
        
        # Search for ticket memories
        search_results = await sms_ctx.qdrant_client.search(
            query_vector=[0.0] * 768,
            limit=10,
            score_threshold=0.0,
            filter_conditions={"ticket_id": ticket_id}
        )
        
        if not search_results:
            console.print(f"❌ No memories found for ticket {ticket_id}", style="red")
            return
        
        # Display results
        table = Table(title=f"Memory Debug: {ticket_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for i, memory in enumerate(search_results):
            payload = memory.payload
            
            console.print(f"\n📋 Memory {i+1} (ID: {memory.point_id})", style="bold")
            
            table = Table()
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Template", payload.template_name)
            table.add_row("Feature", payload.feature_id)
            table.add_row("Complexity", f"{payload.complexity_score:.2f}")
            table.add_row("Retry Count", str(payload.retry_count))
            table.add_row("Files Touched", str(len(payload.files_touched)))
            table.add_row("Connected Features", str(len(payload.connected_features)))
            table.add_row("Created At", payload.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            
            console.print(table)
            
            # Show files touched
            if payload.files_touched:
                console.print("\n📁 Files Touched:", style="bold")
                for file_path in payload.files_touched:
                    console.print(f"  • {file_path}")
            
            # Show connected features
            if payload.connected_features:
                console.print("\n🔗 Connected Features:", style="bold")
                for feature in payload.connected_features:
                    console.print(f"  • {feature}")
    
    asyncio.run(_debug())

@sms.command()
@click.argument('ticket_id')
@click.pass_context
def session_history(ctx, ticket_id: str):
    """View session history for a ticket"""
    async def _session_history():
        sms_ctx = ctx.obj['sms_context']
        await sms_ctx.initialize()
        
        console.print(f"📚 Session history for: {ticket_id}", style="bold blue")
        
        # Get all memories for this ticket
        search_results = await sms_ctx.qdrant_client.search(
            query_vector=[0.0] * 768,
            limit=100,
            score_threshold=0.0,
            filter_conditions={"ticket_id": ticket_id}
        )
        
        if not search_results:
            console.print(f"❌ No session history found for ticket {ticket_id}", style="red")
            return
        
        # Sort by creation time
        sorted_memories = sorted(search_results, key=lambda m: m.payload.created_at)
        
        # Display timeline
        tree = Tree(f"Session Timeline - {ticket_id}")
        
        for memory in sorted_memories:
            payload = memory.payload
            timestamp = payload.created_at.strftime("%H:%M:%S")
            
            node_text = f"{timestamp} - {payload.template_name} (complexity: {payload.complexity_score:.2f})"
            if payload.retry_count > 0:
                node_text += f" [retry: {payload.retry_count}]"
            
            tree.add(node_text)
        
        console.print(tree)
        
        # Summary statistics
        complexity_scores = [m.payload.complexity_score for m in sorted_memories]
        retry_counts = [m.payload.retry_count for m in sorted_memories]
        
        console.print("\n📊 Session Summary:", style="bold")
        console.print(f"  Total interactions: {len(sorted_memories)}")
        console.print(f"  Average complexity: {sum(complexity_scores) / len(complexity_scores):.2f}")
        console.print(f"  Total retries: {sum(retry_counts)}")
        console.print(f"  Session duration: {(sorted_memories[-1].payload.created_at - sorted_memories[0].payload.created_at).total_seconds() / 60:.1f} minutes")
    
    asyncio.run(_session_history())

@sms.command()
@click.option('--feature', required=True, help='Feature ID to visualize')
@click.pass_context
def graph_viz(ctx, feature: str):
    """Visualize memory graph for a feature"""
    async def _graph_viz():
        sms_ctx = ctx.obj['sms_context']
        await sms_ctx.initialize()
        
        console.print(f"🕸️  Memory graph for feature: {feature}", style="bold blue")
        
        # Get feature graph
        graph_data = await sms_ctx.graph_manager.get_feature_graph(feature)
        
        if not graph_data.nodes:
            console.print(f"❌ No graph data found for feature {feature}", style="red")
            return
        
        # Display graph structure
        tree = Tree(f"Feature Graph - {feature}")
        
        # Group nodes by type
        file_nodes = [n for n in graph_data.nodes if n.node_type == "file"]
        feature_nodes = [n for n in graph_data.nodes if n.node_type == "feature"]
        
        # Add file nodes
        if file_nodes:
            files_branch = tree.add("📁 Files")
            for node in file_nodes:
                files_branch.add(f"{node.node_id} (weight: {node.weight:.2f})")
        
        # Add feature nodes
        if feature_nodes:
            features_branch = tree.add("🎯 Features")
            for node in feature_nodes:
                features_branch.add(f"{node.node_id} (weight: {node.weight:.2f})")
        
        console.print(tree)
        
        # Display edge statistics
        console.print(f"\n🔗 Graph Statistics:", style="bold")
        console.print(f"  Total nodes: {len(graph_data.nodes)}")
        console.print(f"  Total edges: {len(graph_data.edges)}")
        console.print(f"  File nodes: {len(file_nodes)}")
        console.print(f"  Feature nodes: {len(feature_nodes)}")
    
    asyncio.run(_graph_viz())

@sms.command()
@click.option('--ticket', required=True, help='Ticket ID to test similarity for')
@click.option('--threshold', default=0.8, type=float, help='Similarity threshold')
@click.pass_context
def similarity_test(ctx, ticket: str, threshold: float):
    """Test vector similarity search"""
    async def _similarity_test():
        sms_ctx = ctx.obj['sms_context']
        await sms_ctx.initialize()
        
        console.print(f"🔍 Similarity test for: {ticket} (threshold: {threshold})", style="bold blue")
        
        # Get the ticket's memory
        ticket_memories = await sms_ctx.qdrant_client.search(
            query_vector=[0.0] * 768,
            limit=1,
            score_threshold=0.0,
            filter_conditions={"ticket_id": ticket}
        )
        
        if not ticket_memories:
            console.print(f"❌ No memories found for ticket {ticket}", style="red")
            return
        
        # Get similar memories
        reference_memory = ticket_memories[0]
        if not reference_memory.vector:
            console.print(f"❌ No vector found for ticket {ticket}", style="red")
            return
        
        similar_memories = await sms_ctx.qdrant_client.search(
            query_vector=reference_memory.vector,
            limit=10,
            score_threshold=threshold
        )
        
        # Display results
        table = Table(title=f"Similar Memories (threshold: {threshold})")
        table.add_column("Ticket ID", style="cyan")
        table.add_column("Template", style="white")
        table.add_column("Feature", style="yellow")
        table.add_column("Similarity", style="green")
        table.add_column("Complexity", style="red")
        
        for memory in similar_memories:
            if memory.point_id != reference_memory.point_id:  # Skip self
                payload = memory.payload
                table.add_row(
                    payload.ticket_id,
                    payload.template_name,
                    payload.feature_id,
                    f"{memory.score:.3f}",
                    f"{payload.complexity_score:.2f}"
                )
        
        console.print(table)
    
    asyncio.run(_similarity_test())

@sms.command()
@click.option('--timeframe', default='7d', help='Time frame for analytics (e.g., 7d, 1m)')
@click.pass_context
def analytics(ctx, timeframe: str):
    """View memory usage analytics"""
    async def _analytics():
        sms_ctx = ctx.obj['sms_context']
        await sms_ctx.initialize()
        
        console.print(f"📊 Memory analytics for: {timeframe}", style="bold blue")
        
        # Get collection statistics
        stats = await sms_ctx.qdrant_client.get_collection_stats()
        
        # Display basic stats
        console.print(Panel.fit(
            f"[bold]Collection Statistics[/bold]\n"
            f"Total points: {stats.get('points_count', 0)}\n"
            f"Vector count: {stats.get('vectors_count', 0)}\n"
            f"Disk usage: {stats.get('disk_data_size', 0) / (1024*1024):.1f} MB\n"
            f"RAM usage: {stats.get('ram_data_size', 0) / (1024*1024):.1f} MB"
        ))
        
        # Get complexity statistics
        complexity_stats = await sms_ctx.complexity_scorer.get_complexity_statistics()
        
        if complexity_stats and "complexity_distribution" in complexity_stats:
            dist = complexity_stats["complexity_distribution"]
            
            console.print("\n📈 Complexity Distribution:", style="bold")
            console.print(f"  Low complexity: {dist.get('low', 0)}")
            console.print(f"  Medium complexity: {dist.get('medium', 0)}")
            console.print(f"  High complexity: {dist.get('high', 0)}")
            console.print(f"  Average complexity: {complexity_stats.get('average_complexity', 0):.3f}")
            console.print(f"  Average retries: {complexity_stats.get('average_retries', 0):.2f}")
        
        # Get graph statistics
        graph_stats = await sms_ctx.graph_manager.get_graph_statistics()
        
        if graph_stats:
            console.print("\n🕸️  Graph Statistics:", style="bold")
            console.print(f"  Unique files: {graph_stats.get('unique_files', 0)}")
            console.print(f"  Unique features: {graph_stats.get('unique_features', 0)}")
            console.print(f"  Cache size: {graph_stats.get('cache_size', 0)}")
    
    asyncio.run(_analytics())

@sms.command()
@click.pass_context
def health(ctx):
    """Check SMS system health"""
    async def _health():
        sms_ctx = ctx.obj['sms_context']
        
        try:
            await sms_ctx.initialize()
            
            # Test Qdrant connection
            qdrant_healthy = await sms_ctx.qdrant_client.test_connection()
            
            # Test OpenAI connection
            openai_healthy = await sms_ctx.embedding_engine.test_connection()
            
            # Display health status
            table = Table(title="System Health Check")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Details", style="yellow")
            
            table.add_row(
                "Qdrant Client",
                "✅ Healthy" if qdrant_healthy else "❌ Unhealthy",
                "Vector database connection"
            )
            
            table.add_row(
                "OpenAI Client",
                "✅ Healthy" if openai_healthy else "❌ Unhealthy",
                "Embedding generation service"
            )
            
            table.add_row(
                "Graph Manager",
                "✅ Healthy" if sms_ctx.graph_manager else "❌ Unhealthy",
                "File-feature relationship tracking"
            )
            
            table.add_row(
                "Context Enricher",
                "✅ Healthy" if sms_ctx.context_enricher else "❌ Unhealthy",
                "Prompt context enhancement"
            )
            
            table.add_row(
                "Complexity Scorer",
                "✅ Healthy" if sms_ctx.complexity_scorer else "❌ Unhealthy",
                "Task complexity analysis"
            )
            
            console.print(table)
            
            overall_healthy = all([qdrant_healthy, openai_healthy])
            
            if overall_healthy:
                console.print("\n🎉 SMS system is healthy!", style="green bold")
            else:
                console.print("\n⚠️  SMS system has issues", style="red bold")
                
        except Exception as e:
            console.print(f"❌ Health check failed: {e}", style="red")
    
    asyncio.run(_health())

if __name__ == "__main__":
    sms() 