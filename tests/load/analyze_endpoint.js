/**
 * Load test for analyze endpoint using k6
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');

// Test configuration
export let options = {
  stages: [
    { duration: '2m', target: 10 }, // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users
    { duration: '2m', target: 20 },  // Ramp up to 20 users
    { duration: '5m', target: 20 }, // Stay at 20 users
    { duration: '2m', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
    http_req_failed: ['rate<0.1'],     // Error rate should be less than 10%
    errors: ['rate<0.1'],              // Custom error rate should be less than 10%
  },
};

// Sample diff content for testing
const sampleDiff = `diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,7 @@ def authenticate_user(username, password):
     user = get_user_by_username(username)
     if user and user.password == password:
+        # TODO: Add password hashing
         return user
     return None
@@ -20,6 +21,8 @@ def create_user(username, password):
-    user = User(username=username, password=password)
+    user = User(username=username, password=password)
+    # Hardcoded password for testing
+    if password == "admin123":
+        return user
     return user`;

// Test data
const testData = {
  repository_url: 'https://github.com/test/repo',
  pull_request_id: Math.floor(Math.random() * 1000),
  diff_content: sampleDiff,
  base_commit: 'abc123',
  head_commit: 'def456',
  file_paths: ['src/auth.py']
};

// Headers
const headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer mock-token'
};

export default function() {
  // Test health endpoint
  let healthResponse = http.get('http://localhost:8000/health/');
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 100ms': (r) => r.timings.duration < 100,
  });
  
  errorRate.add(healthResponse.status !== 200);

  // Test analyze endpoint
  let analyzeResponse = http.post(
    'http://localhost:8000/api/v1/analyze/',
    JSON.stringify(testData),
    { headers: headers }
  );

  check(analyzeResponse, {
    'analyze request status is 200': (r) => r.status === 200,
    'analyze request has review_id': (r) => JSON.parse(r.body).review_id !== undefined,
    'analyze request response time < 2s': (r) => r.timings.duration < 2000,
  });

  errorRate.add(analyzeResponse.status !== 200);

  // If we got a review_id, test getting the result
  if (analyzeResponse.status === 200) {
    let reviewId = JSON.parse(analyzeResponse.body).review_id;
    
    // Wait a bit for processing
    sleep(1);
    
    let resultResponse = http.get(
      `http://localhost:8000/api/v1/analyze/${reviewId}`,
      { headers: headers }
    );

    check(resultResponse, {
      'result request status is 200': (r) => r.status === 200,
      'result request response time < 500ms': (r) => r.timings.duration < 500,
    });

    errorRate.add(resultResponse.status !== 200);
  }

  // Test feedback endpoint
  let feedbackData = {
    review_id: 'test-review-id',
    suggestion_id: 'suggestion-1',
    helpful: Math.random() > 0.5,
    correction: 'Test feedback',
    category: 'security'
  };

  let feedbackResponse = http.post(
    'http://localhost:8000/api/v1/feedback/',
    JSON.stringify(feedbackData),
    { headers: headers }
  );

  check(feedbackResponse, {
    'feedback request status is 200': (r) => r.status === 200,
    'feedback request response time < 500ms': (r) => r.timings.duration < 500,
  });

  errorRate.add(feedbackResponse.status !== 200);

  // Test metrics endpoint
  let metricsResponse = http.get('http://localhost:8000/metrics');
  check(metricsResponse, {
    'metrics request status is 200': (r) => r.status === 200,
    'metrics request response time < 200ms': (r) => r.timings.duration < 200,
  });

  errorRate.add(metricsResponse.status !== 200);

  // Random sleep between requests
  sleep(Math.random() * 2);
}

export function handleSummary(data) {
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    stdout: `
Load Test Results:
==================
Total Requests: ${data.metrics.http_reqs.values.count}
Failed Requests: ${data.metrics.http_req_failed.values.count}
Average Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
95th Percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
    `,
  };
}
