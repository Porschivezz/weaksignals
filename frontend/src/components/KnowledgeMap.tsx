"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import type { GraphNode, GraphEdge } from "@/lib/types";

export interface KnowledgeMapZoomControls {
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
}

interface KnowledgeMapProps {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
  width?: number;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
  onZoomControlsReady?: (controls: KnowledgeMapZoomControls) => void;
}

const MOCK_NODES: GraphNode[] = [
  { id: "transformer", label: "Transformer Architecture", type: "architecture", size: 28 },
  { id: "moe", label: "Mixture of Experts", type: "architecture", size: 22 },
  { id: "lora", label: "LoRA Fine-tuning", type: "technique", size: 20 },
  { id: "rag", label: "RAG", type: "technique", size: 24 },
  { id: "agents", label: "AI Agents", type: "application", size: 26 },
  { id: "multimodal", label: "Multimodal Models", type: "architecture", size: 23 },
  { id: "rlhf", label: "RLHF", type: "technique", size: 18 },
  { id: "quantization", label: "Quantization", type: "optimization", size: 16 },
  { id: "distillation", label: "Knowledge Distillation", type: "optimization", size: 15 },
  { id: "prompt_eng", label: "Prompt Engineering", type: "technique", size: 17 },
  { id: "embedding", label: "Embedding Models", type: "architecture", size: 19 },
  { id: "vector_db", label: "Vector Databases", type: "infrastructure", size: 21 },
  { id: "diffusion", label: "Diffusion Models", type: "architecture", size: 20 },
  { id: "code_gen", label: "Code Generation", type: "application", size: 22 },
  { id: "reasoning", label: "Chain-of-Thought", type: "technique", size: 19 },
  { id: "synthetic_data", label: "Synthetic Data", type: "technique", size: 17 },
  { id: "edge_ai", label: "Edge AI Inference", type: "infrastructure", size: 14 },
  { id: "alignment", label: "AI Alignment", type: "safety", size: 18 },
  { id: "hallucination", label: "Hallucination Mitigation", type: "safety", size: 16 },
  { id: "llm_ops", label: "LLMOps", type: "infrastructure", size: 15 },
];

const MOCK_EDGES: GraphEdge[] = [
  { source: "transformer", target: "moe", weight: 0.8, type: "evolution" },
  { source: "transformer", target: "multimodal", weight: 0.9, type: "foundation" },
  { source: "transformer", target: "diffusion", weight: 0.5, type: "related" },
  { source: "lora", target: "transformer", weight: 0.7, type: "optimizes" },
  { source: "rag", target: "vector_db", weight: 0.9, type: "requires" },
  { source: "rag", target: "embedding", weight: 0.85, type: "uses" },
  { source: "agents", target: "rag", weight: 0.7, type: "uses" },
  { source: "agents", target: "reasoning", weight: 0.8, type: "uses" },
  { source: "agents", target: "code_gen", weight: 0.6, type: "enables" },
  { source: "rlhf", target: "alignment", weight: 0.8, type: "contributes" },
  { source: "quantization", target: "edge_ai", weight: 0.7, type: "enables" },
  { source: "distillation", target: "quantization", weight: 0.5, type: "related" },
  { source: "prompt_eng", target: "reasoning", weight: 0.6, type: "related" },
  { source: "code_gen", target: "transformer", weight: 0.6, type: "based_on" },
  { source: "synthetic_data", target: "lora", weight: 0.5, type: "used_with" },
  { source: "hallucination", target: "rag", weight: 0.7, type: "mitigated_by" },
  { source: "hallucination", target: "alignment", weight: 0.6, type: "related" },
  { source: "llm_ops", target: "quantization", weight: 0.5, type: "includes" },
  { source: "llm_ops", target: "lora", weight: 0.4, type: "manages" },
  { source: "multimodal", target: "diffusion", weight: 0.6, type: "related" },
  { source: "moe", target: "distillation", weight: 0.4, type: "related" },
];

const TYPE_COLORS: Record<string, string> = {
  architecture: "#3b82f6",
  technique: "#f59e0b",
  application: "#10b981",
  optimization: "#8b5cf6",
  infrastructure: "#06b6d4",
  safety: "#ef4444",
};

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
  size: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  weight: number;
  type: string;
}

export default function KnowledgeMap({
  nodes: propNodes,
  edges: propEdges,
  width: propWidth,
  height: propHeight,
  onNodeClick,
  onZoomControlsReady,
}: KnowledgeMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [dimensions, setDimensions] = useState({ width: propWidth || 800, height: propHeight || 500 });

  const graphNodes = propNodes || MOCK_NODES;
  const graphEdges = propEdges || MOCK_EDGES;

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: propWidth || entry.contentRect.width || 800,
          height: propHeight || entry.contentRect.height || 500,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [propWidth, propHeight]);

  const renderGraph = useCallback(() => {
    if (!svgRef.current) return;

    const { width, height } = dimensions;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const simNodes: SimNode[] = graphNodes.map((n) => ({ ...n }));
    const simLinks: SimLink[] = graphEdges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
      type: e.type,
    }));

    const g = svg.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    if (onZoomControlsReady) {
      onZoomControlsReady({
        zoomIn: () => svg.transition().duration(300).call(zoom.scaleBy, 1.5),
        zoomOut: () => svg.transition().duration(300).call(zoom.scaleBy, 0.67),
        resetZoom: () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity),
      });
    }

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(100)
          .strength((d) => d.weight * 0.3)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d) => (d as SimNode).size + 10));

    const link = g
      .append("g")
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke", "#334155")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d) => Math.max(1, d.weight * 3));

    const nodeGroup = g
      .append("g")
      .selectAll("g")
      .data(simNodes)
      .join("g")
      .style("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as any
      );

    nodeGroup
      .append("circle")
      .attr("r", (d) => d.size)
      .attr("fill", (d) => TYPE_COLORS[d.type] || "#64748b")
      .attr("fill-opacity", 0.2)
      .attr("stroke", (d) => TYPE_COLORS[d.type] || "#64748b")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.8);

    nodeGroup
      .append("text")
      .text((d) => d.label)
      .attr("text-anchor", "middle")
      .attr("dy", (d) => d.size + 14)
      .attr("font-size", "10px")
      .attr("fill", "#94a3b8")
      .attr("pointer-events", "none");

    nodeGroup.on("click", (_event, d) => {
      const node: GraphNode = { id: d.id, label: d.label, type: d.type, size: d.size };
      setSelectedNode(node);
      onNodeClick?.(node);
    });

    nodeGroup
      .on("mouseover", function (_, d) {
        d3.select(this)
          .select("circle")
          .transition()
          .duration(200)
          .attr("fill-opacity", 0.4)
          .attr("stroke-width", 2.5);

        link
          .attr("stroke-opacity", (l) => {
            const src = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
            const tgt = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
            return src === d.id || tgt === d.id ? 1 : 0.1;
          })
          .attr("stroke", (l) => {
            const src = typeof l.source === "object" ? (l.source as SimNode).id : l.source;
            const tgt = typeof l.target === "object" ? (l.target as SimNode).id : l.target;
            return src === d.id || tgt === d.id
              ? TYPE_COLORS[d.type] || "#64748b"
              : "#334155";
          });
      })
      .on("mouseout", function () {
        d3.select(this)
          .select("circle")
          .transition()
          .duration(200)
          .attr("fill-opacity", 0.2)
          .attr("stroke-width", 1.5);

        link.attr("stroke-opacity", 0.6).attr("stroke", "#334155");
      });

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);

      nodeGroup.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [graphNodes, graphEdges, dimensions, onNodeClick]);

  useEffect(() => {
    const cleanup = renderGraph();
    return () => cleanup?.();
  }, [renderGraph]);

  const filteredHighlight = searchTerm.toLowerCase();

  return (
    <div className="relative w-full h-full" ref={containerRef}>
      {/* Search */}
      <div className="absolute top-3 left-3 z-10">
        <input
          type="text"
          placeholder="Search concepts..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input-field w-56 text-xs py-1.5 bg-slate-900/90"
        />
      </div>

      {/* Legend */}
      <div className="absolute top-3 right-3 z-10 bg-slate-900/90 border border-slate-800 rounded-lg p-3 backdrop-blur-sm">
        <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Node Types</p>
        <div className="space-y-1.5">
          {Object.entries(TYPE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-[11px] text-slate-400 capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected node detail */}
      {selectedNode && (
        <div className="absolute bottom-3 left-3 z-10 bg-slate-900/95 border border-slate-700 rounded-lg p-4 backdrop-blur-sm max-w-xs animate-slide-up">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-white">{selectedNode.label}</h4>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-500 hover:text-slate-300 text-xs"
            >
              Close
            </button>
          </div>
          <div className="space-y-1 text-xs text-slate-400">
            <div>
              Type:{" "}
              <span
                className="capitalize font-medium"
                style={{ color: TYPE_COLORS[selectedNode.type] }}
              >
                {selectedNode.type}
              </span>
            </div>
            <div>Importance: {selectedNode.size}/30</div>
            <div>
              Connections:{" "}
              {graphEdges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id).length}
            </div>
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        className="w-full h-full"
        style={{
          opacity: searchTerm ? 0.7 : 1,
        }}
      />
    </div>
  );
}
