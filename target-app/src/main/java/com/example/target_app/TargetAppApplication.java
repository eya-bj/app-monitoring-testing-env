package com.example.target_app;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class TargetAppApplication {

	public static void main(String[] args) {
		SpringApplication.run(TargetAppApplication.class, args);
	}

}
