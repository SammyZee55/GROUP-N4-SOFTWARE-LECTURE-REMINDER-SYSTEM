// ------------------- Dark Mode Toggle -------------------
const darkModeToggle = document.getElementById("darkModeToggle");

// Apply saved preference on page load
if (localStorage.getItem("darkMode") === "enabled") {
    document.body.classList.add("dark");
}

// Toggle dark mode on button click
if (darkModeToggle) {
    darkModeToggle.addEventListener("click", () => {
        document.body.classList.toggle("dark");
        if (document.body.classList.contains("dark")) {
            localStorage.setItem("darkMode", "enabled");
        } else {
            localStorage.setItem("darkMode", "disabled");
        }
    });
}

// ------------------- Browser Notifications -------------------
document.addEventListener("DOMContentLoaded", () => {
    if (!("Notification" in window)) {
        console.log("This browser does not support notifications.");
        return;
    }

    // Ask permission if not already granted
    if (Notification.permission !== "granted") {
        Notification.requestPermission();
    }

    // Display today's reminders if on dashboard
    const todayRemindersList = document.querySelectorAll("#todayReminders li");
    if (todayRemindersList.length > 0 && Notification.permission === "granted") {
        todayRemindersList.forEach(rem => {
            const reminderText = rem.textContent;
            new Notification("Today's Reminder", {
                body: reminderText,
                icon: "" // Optional: add icon URL here
            });
        });
    }
});
