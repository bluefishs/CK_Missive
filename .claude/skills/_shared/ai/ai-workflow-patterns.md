# AI Workflow Patterns

> **版本**: 1.0.0
> **適用**: AI 整合專案
> **觸發**: AI 工作流, 智能流程, 自動化, Agent

---

## 概述

本 Skill 定義 AI 驅動工作流的設計模式與實作指南。

---

## 工作流模式

### 1. 鏈式處理 (Chain)

```
Input → [Step 1] → [Step 2] → [Step 3] → Output
         ↓           ↓           ↓
      Transform   Analyze     Generate
```

```typescript
class AIChain {
  private steps: ChainStep[] = [];

  add(step: ChainStep): this {
    this.steps.push(step);
    return this;
  }

  async run(input: any): Promise<any> {
    let result = input;
    for (const step of this.steps) {
      result = await step.process(result);
    }
    return result;
  }
}
```

### 2. 分支處理 (Router)

```
           ┌→ [Handler A] →┐
Input → [Router]           [Merge] → Output
           └→ [Handler B] →┘
```

```typescript
class AIRouter {
  private routes: Map<string, Handler> = new Map();

  route(condition: string, handler: Handler): this {
    this.routes.set(condition, handler);
    return this;
  }

  async process(input: any): Promise<any> {
    const category = await this.classify(input);
    const handler = this.routes.get(category);
    return handler.process(input);
  }
}
```

### 3. 並行處理 (Parallel)

```
         ┌→ [Task A] →┐
Input →  ├→ [Task B] →┼→ [Aggregate] → Output
         └→ [Task C] →┘
```

```typescript
async function parallelProcess(
  input: any,
  tasks: Task[]
): Promise<any[]> {
  return Promise.all(
    tasks.map(task => task.process(input))
  );
}
```

### 4. 迴圈處理 (Loop)

```
Input → [Process] → [Evaluate] ─┬─ Done → Output
             ↑                   │
             └───── Retry ───────┘
```

```typescript
async function loopUntilSatisfied(
  input: any,
  process: (x: any) => Promise<any>,
  evaluate: (x: any) => boolean,
  maxIterations: number = 5
): Promise<any> {
  let result = input;
  let iterations = 0;

  while (!evaluate(result) && iterations < maxIterations) {
    result = await process(result);
    iterations++;
  }

  return result;
}
```

---

## 實用工作流範例

### 文件分析工作流

```typescript
const documentAnalysis = new AIChain()
  .add(new ExtractTextStep())
  .add(new ClassifyContentStep())
  .add(new ExtractEntitiesStep())
  .add(new GenerateSummaryStep())
  .add(new FormatOutputStep());

const result = await documentAnalysis.run(document);
```

### 智能問答工作流

```typescript
const qaWorkflow = new AIRouter()
  .route('factual', new FactualQAHandler())
  .route('analytical', new AnalyticalQAHandler())
  .route('creative', new CreativeQAHandler())
  .route('code', new CodeQAHandler());

const answer = await qaWorkflow.process(question);
```

---

## Agent 模式

### 基礎 Agent 結構

```typescript
interface Agent {
  name: string;
  description: string;
  tools: Tool[];

  think(context: Context): Promise<Action>;
  act(action: Action): Promise<Result>;
  reflect(result: Result): Promise<void>;
}
```

### ReAct 模式

```
Thought → Action → Observation → Thought → ...
```

```typescript
async function reactLoop(
  agent: Agent,
  goal: string,
  maxSteps: number = 10
): Promise<Result> {
  const context = new Context(goal);

  for (let i = 0; i < maxSteps; i++) {
    const thought = await agent.think(context);

    if (thought.type === 'final_answer') {
      return thought.answer;
    }

    const action = await agent.act(thought);
    const observation = await executeAction(action);
    context.add(observation);
  }

  throw new Error('Max steps exceeded');
}
```

---

## 監控與可觀察性

### 工作流追蹤

```typescript
interface WorkflowTrace {
  id: string;
  startTime: Date;
  endTime?: Date;
  steps: StepTrace[];
  status: 'running' | 'completed' | 'failed';
  error?: Error;
}
```

### 指標收集

- 執行時間
- Token 使用量
- 成功/失敗率
- 每步驟延遲

---

## 檢查清單

- [ ] 工作流步驟定義清晰
- [ ] 錯誤處理覆蓋各步驟
- [ ] 有適當的超時機制
- [ ] 支援工作流追蹤
- [ ] 可配置重試策略

---

*版本：1.0.0 | 適用領域：AI 整合專案*
