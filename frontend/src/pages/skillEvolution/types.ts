/**
 * Skill Evolution Tree - Type Definitions
 *
 * @version 1.0.0
 */

export interface SkillNode {
  id: number;
  name: string;
  category: string;
  version: string;
  maturity: number;
  source: string;
  description: string;
  size: number;
  children: string[];
}

export interface SkillEdge {
  source: number;
  target: number;
  type: string;
  label: string;
}

export interface CategoryInfo {
  label: string;
  color: string;
  icon: string;
}

export interface SkillEvolutionStats {
  total: number;
  active: number;
  planned: number;
  merged: number;
  evolution_count: number;
  merge_count: number;
}

export interface SkillEvolutionData {
  nodes: SkillNode[];
  edges: SkillEdge[];
  categories: Record<string, CategoryInfo>;
  stats: SkillEvolutionStats;
}

/** Force graph node with x/y coordinates added by the engine */
export interface GraphNode extends SkillNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

/** Force graph link with resolved source/target */
export interface GraphLink {
  source: number | GraphNode;
  target: number | GraphNode;
  type: string;
  label: string;
}

export interface ForceGraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}
