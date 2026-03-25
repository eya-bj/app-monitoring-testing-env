with open("daily_report_2026-03-24.csv", "w") as f:
    f.write("date,amount,currency,status\n")
    for i in range(1, 201):
        f.write(f"2026-03-24,{i * 100},USD,SUCCESS\n")
print("File generated!")