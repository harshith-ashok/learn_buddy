// Load test for the two endpoints wiki/plan.md's KPI table sets latency
// targets on:
//   - GET  /recommendation/next   < 3s  (p95)
//   - POST /study-kit/generate    < 15s (p95, cold)
//
// Run from backend/: `k6 run load-tests/recommendation_and_study_kit.js`
// after `uv run python load-tests/seed.py` — see load-tests/README.md.
import http from "k6/http";
import { check } from "k6";
import { SharedArray } from "k6/data";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const users = new SharedArray("load-test users", function () {
  return JSON.parse(open("./seed-data.json"));
});

export const options = {
  scenarios: {
    recommendation: {
      executor: "constant-vus",
      vus: Number(__ENV.RECOMMENDATION_VUS || 10),
      duration: __ENV.DURATION || "30s",
      exec: "recommendationNext",
    },
    study_kit_generate: {
      executor: "constant-vus",
      vus: Number(__ENV.STUDY_KIT_VUS || 5),
      duration: __ENV.DURATION || "30s",
      exec: "studyKitGenerate",
      startTime: "5s", // stagger so both scenarios' ramp-up doesn't collide
    },
  },
  thresholds: {
    "http_req_duration{endpoint:recommendation}": ["p(95)<3000"],
    "http_req_duration{endpoint:study_kit_generate}": ["p(95)<15000"],
    "checks{endpoint:recommendation}": ["rate>0.99"],
    // 429 is an expected, correct response once a seeded user's
    // STUDY_KIT_GENERATION_RATE_LIMIT budget is spent for the run — the
    // check below accepts it, so this threshold still means "no 4xx/5xx
    // surprises", not "no rate limiting happened".
    "checks{endpoint:study_kit_generate}": ["rate>0.99"],
  },
};

function pickUser() {
  return users[Math.floor(Math.random() * users.length)];
}

export function recommendationNext() {
  const user = pickUser();
  const res = http.get(`${BASE_URL}/recommendation/next`, {
    headers: { Authorization: `Bearer ${user.access_token}` },
    tags: { endpoint: "recommendation" },
  });
  check(res, { "status is 200": (r) => r.status === 200 }, { endpoint: "recommendation" });
}

export function studyKitGenerate() {
  const user = pickUser();
  const res = http.post(
    `${BASE_URL}/study-kit/generate`,
    JSON.stringify({ topic_id: user.topic_id, kit_type: "summary" }),
    {
      headers: {
        Authorization: `Bearer ${user.access_token}`,
        "Content-Type": "application/json",
      },
      tags: { endpoint: "study_kit_generate" },
    },
  );
  check(
    res,
    {
      "status is 201 (generated), 200 (not covered), or 429 (rate limited)": (r) =>
        [200, 201, 429].includes(r.status),
    },
    { endpoint: "study_kit_generate" },
  );
}
