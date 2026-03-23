"use client";

import { useState, useEffect } from "react";
import { Search, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import type { GraphNode, LandscapeData } from "@/lib/types";
import { getLandscape } from "@/lib/api";
import KnowledgeMap from "@/components/KnowledgeMap";

export default function LandscapePage() {
  const [landscapeData, setLandscapeData] = useState<LandscapeData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    async function fetchLandscape() {
      try {
        const data = await getLandscape();
        if (data && data.nodes.length > 0) {
          setLandscapeData(data);
        }
      } catch {
        // Use built-in mock data from KnowledgeMap
      }
    }
    fetchLandscape();
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Knowledge Landscape</h1>
          <p className="text-sm text-slate-500 mt-1">
            Interactive map of AI technology concepts, relationships, and emerging clusters
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-ghost">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button className="btn-ghost">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button className="btn-ghost">
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main visualization */}
      <div className="card p-0 overflow-hidden" style={{ height: "calc(100vh - 200px)" }}>
        <KnowledgeMap
          nodes={landscapeData?.nodes}
          edges={landscapeData?.edges}
          onNodeClick={(node) => setSelectedNode(node)}
        />
      </div>

      {/* Info bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card-compact text-center">
          <p className="text-2xl font-bold text-white">20</p>
          <p className="text-xs text-slate-500 mt-1">Technology Concepts</p>
        </div>
        <div className="card-compact text-center">
          <p className="text-2xl font-bold text-white">21</p>
          <p className="text-xs text-slate-500 mt-1">Relationships Mapped</p>
        </div>
        <div className="card-compact text-center">
          <p className="text-2xl font-bold text-white">6</p>
          <p className="text-xs text-slate-500 mt-1">Concept Categories</p>
        </div>
        <div className="card-compact text-center">
          <p className="text-2xl font-bold text-blue-400">
            {selectedNode ? selectedNode.label : "None selected"}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {selectedNode ? `Type: ${selectedNode.type}` : "Click a node to inspect"}
          </p>
        </div>
      </div>
    </div>
  );
}
