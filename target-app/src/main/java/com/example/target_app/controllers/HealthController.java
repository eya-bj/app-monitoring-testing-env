package com.example.target_app.controllers;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.Random;
import java.util.concurrent.atomic.AtomicBoolean;

@RestController

// This controller simulates the health status of the application. It allows toggling between UP and DOWN states for testing purposes.
public class HealthController {
    private final AtomicBoolean randomMode = new AtomicBoolean(false);
    private final Random random = new Random();
    private final AtomicBoolean isDown = new AtomicBoolean(false);

    @GetMapping("/actuator/health")
    public ResponseEntity<Map<String, String>> health() {
        if (isDown.get()) {
            return ResponseEntity.status(503)
                    .body(Map.of("status", "DOWN"));
        }
        if (randomMode.get()) {
            // 66% chance UP, 33% chance DOWN
            if (random.nextInt(3) == 0) {
                return ResponseEntity.status(503)
                        .body(Map.of("status", "DOWN"));
            }
        }
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @PostMapping("/simulate/random")
    public ResponseEntity<String> simulateRandom() {
        randomMode.set(true);
        isDown.set(false);
        return ResponseEntity.ok("App is now in RANDOM mode (66% UP / 33% DOWN)");
    }

    @PostMapping("/simulate/stable")
    public ResponseEntity<String> simulateStable() {
        randomMode.set(false);
        isDown.set(false);
        return ResponseEntity.ok("App is now STABLE");
    }
}
