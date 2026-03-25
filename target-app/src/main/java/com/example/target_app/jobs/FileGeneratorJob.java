package com.example.target_app.jobs;
import com.jcraft.jsch.*;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
@Component
public class FileGeneratorJob {
    @Value("${sftp.host}") private String host;
    @Value("${sftp.port:22}") private int port;
    @Value("${sftp.username}") private String username;
    @Value("${sftp.password}") private String password;
    @Value("${sftp.folder:/reports}") private String folder;

    @Scheduled(cron = "0 0 * * * *")
    public void generate() {
        String fileName = "daily_report_" + LocalDate.now() + ".csv";
        String content = buildCsv();
        upload(fileName, content);
    }

    private String buildCsv() {
        StringBuilder sb = new StringBuilder();
        sb.append("date,amount,currency,status\n");
        for (int i = 1; i <= 200; i++) {
            sb.append(LocalDate.now()).append(",")
                    .append(i * 100).append(",USD,SUCCESS\n");
        }
        return sb.toString();
    }

    private void upload(String fileName, String content) {
        JSch jsch = new JSch();
        Session session = null;
        ChannelSftp channel = null;
        try {
            session = jsch.getSession(username, host, port);
            session.setPassword(password);
            session.setConfig("StrictHostKeyChecking", "no");
            session.connect(10000);
            channel = (ChannelSftp) session.openChannel("sftp");
            channel.connect();
            byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
            channel.put(new ByteArrayInputStream(bytes),
                    folder + "/" + fileName);
        } catch (Exception e) {
            System.err.println("SFTP upload failed: " + e.getMessage());
        } finally {
            if (channel != null) channel.disconnect();
            if (session != null) session.disconnect();
        }
    }
}
