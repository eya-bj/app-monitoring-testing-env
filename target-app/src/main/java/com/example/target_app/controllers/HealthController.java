package com.example.target_app.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

@RestController

// This controller simulates the health status of the application. It allows toggling between UP and DOWN states for testing purposes.
public class HealthController {
    private final AtomicBoolean isDown = new AtomicBoolean(false);

    @GetMapping("/actuator/health")
    public ResponseEntity<Map<String, String>> health() {
        if (isDown.get()) {
            return ResponseEntity.status(503)
                    .body(Map.of("status", "DOWN"));
        }
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @PostMapping("/simulate/down")
    public ResponseEntity<String> simulateDown() {
        isDown.set(true);
        return ResponseEntity.ok("App is now DOWN");
    }

    @PostMapping("/simulate/up")
    public ResponseEntity<String> simulateUp() {
        isDown.set(false);
        return ResponseEntity.ok("App is now UP");
    }
}
