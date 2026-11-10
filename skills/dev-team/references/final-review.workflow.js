export const meta = {
  name: 'dev-team-final-review',
  description: 'Review the feature per dimension, then adversarially verify serious findings',
  phases: [{ title: 'Review' }, { title: 'Verify' }],
}

const FINDINGS = { type: 'object', required: ['findings'], properties: {
  findings: { type: 'array', items: { type: 'object',
    required: ['title', 'file', 'severity', 'scenario', 'fix'], properties: {
      title: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
      severity: { type: 'string', enum: ['critical', 'high', 'blocker', 'major', 'medium', 'minor', 'low'] },
      scenario: { type: 'string' }, fix: { type: 'string' } } } } } }
const VERDICT = { type: 'object', required: ['status', 'reason'], properties: {
  status: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] },
  reason: { type: 'string' } } }

// Plugin agents are namespaced; the leader passes the prefix it sees in the agent list.
const P = args.agentPrefix ?? 'ai-dev-team:'
const AGENT = { correctness: `${P}code-reviewer`, security: `${P}security-auditor`, ui: `${P}ui-ux-designer` }
const SKILL = { correctness: `${P}code-review-checklist`, security: `${P}security-review-checklist`, ui: `${P}ui-ux-design (Design QA section)` }
const SERIOUS = ['critical', 'high', 'blocker', 'major']
const ctx = `Scope: ${args.scope}\nSpec: ${args.specPath}\nDesign: ${args.designPath}\nDo not run test suites, builds or audits: QA sign-off already ran the full suite. Run at most one specific test via .claude/team/run-heavy.sh to prove a finding.`

// Shared cap on concurrent agents so the final review stays inside the resource budget.
const LIMIT = Math.max(1, args.maxAgents ?? 4)
let active = 0
const waiting = []
const slot = async run => {
  while (active >= LIMIT) await new Promise(resolve => waiting.push(resolve))
  active++
  try { return await run() } finally { active--; waiting.shift()?.() }
}

const results = await pipeline(
  args.dimensions,
  d => slot(() => agent(
    `Final ${d} review of the feature. Follow the ${SKILL[d]} skill.\n${ctx}\nReturn findings JSON only; empty array if none.`,
    { agentType: AGENT[d], label: `review:${d}`, phase: 'Review', schema: FINDINGS }))
    .then(r => (r ? r.findings.map(f => ({ ...f, dimension: d })) : null)),
  findings => findings === null ? null : parallel(findings.map(f => () =>
    SERIOUS.includes(f.severity)
      ? slot(() => agent(
          `Adversarially verify this finding. Try to refute it by reading the code, callers, guards and tests. confirmed = reachable failure; refuted = prevented; uncertain = cannot decide.\n${JSON.stringify(f)}\n${ctx}`,
          { agentType: AGENT[f.dimension], label: `verify:${f.file}`, phase: 'Verify', schema: VERDICT, effort: 'high' }))
          .then(v => ({ ...f, verdict: v ?? { status: 'uncertain', reason: 'verifier failed' } }))
      : Promise.resolve({ ...f, verdict: { status: 'unverified', reason: 'minor severity' } })))
)

const missing = results.filter(r => r === null).length
if (missing) log(`${missing} review dimension(s) failed and are missing from the result`)
const all = results.filter(Boolean).flat().filter(Boolean)
const confirmed = all.filter(f => f.verdict.status === 'confirmed')
const uncertain = all.filter(f => f.verdict.status === 'uncertain')
const minor = all.filter(f => f.verdict.status === 'unverified')
log(`${all.length} findings: ${confirmed.length} confirmed, ${uncertain.length} uncertain, ${minor.length} minor`)
return { confirmed, uncertain, minor, missingDimensions: missing }
