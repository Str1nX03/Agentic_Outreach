document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startBtn');
    const dryRunToggle = document.getElementById('dryRunToggle');
    const autoPilotToggle = document.getElementById('autoPilotToggle');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const percentageText = document.getElementById('percentageText');
    const totalCount = document.getElementById('totalCount');
    const successCount = document.getElementById('successCount');
    const failedCount = document.getElementById('failedCount');
    const logConsole = document.getElementById('logConsole');
    
    // Editor UI
    const editRecipient = document.getElementById('editRecipient');
    const editSubject = document.getElementById('editSubject');
    const editBody = document.getElementById('editBody');
    const skipBtn = document.getElementById('skipBtn');
    const approveBtn = document.getElementById('approveBtn');

    let contacts = [];
    let currentIndex = 0;
    let successfulCountNum = 0;
    let failedCountNum = 0;
    let companyCache = {};
    let isRunning = false;

    function addLog(message, type = 'system') {
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logConsole.appendChild(entry);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    startBtn.addEventListener('click', async () => {
        if (isRunning) return;
        
        isRunning = true;
        startBtn.disabled = true;
        startBtn.textContent = '⏳ Loading...';
        
        // Reset UI
        progressBar.style.width = '0%';
        percentageText.textContent = '0%';
        successfulCountNum = 0;
        failedCountNum = 0;
        successCount.textContent = '0';
        failedCount.textContent = '0';
        logConsole.innerHTML = '';
        
        addLog("Fetching contact list from Excel...", "system");

        try {
            const response = await fetch('/contacts');
            const data = await response.json();
            
            contacts = data.hr_names.map((name, i) => ({
                hr_name: name,
                company_name: data.company_names[i],
                email: data.emails[i]
            }));
            
            totalCount.textContent = contacts.length;
            addLog(`Loaded ${contacts.length} contacts. Starting pipeline...`, 'success');
            
            currentIndex = 0;
            processNextContact();
        } catch (error) {
            addLog(`Error fetching contacts: ${error.message}`, 'error');
            isRunning = false;
            startBtn.disabled = false;
            startBtn.textContent = '▶ Start Campaign';
        }
    });

    async function processNextContact() {
        updateProgress();

        if (currentIndex >= contacts.length) {
            addLog("Campaign Finished!", "success");
            isRunning = false;
            startBtn.disabled = false;
            startBtn.textContent = "▶ Start Campaign";
            return;
        }

        const contact = contacts[currentIndex];
        addLog(`Drafting email for ${contact.hr_name} (${contact.company_name})...`, 'system');
        
        try {
            const response = await fetch('/draft-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    hr_name: contact.hr_name,
                    company_name: contact.company_name,
                    email: contact.email,
                    company_cache: companyCache
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Server error while drafting");
            }

            const draft = await response.json();
            
            // Update local cache from the draft result
            if (draft.company && draft.product && draft.pain_points) {
                companyCache[draft.company] = {
                    product: draft.product,
                    pain_points: draft.pain_points
                };
            }

            if (autoPilotToggle.checked) {
                addLog(`Auto-Pilot: Sending to ${contact.hr_name}...`, 'system');
                await sendEmail(draft.email, draft.subject, draft.body);
            } else {
                displayDraft(draft);
            }
        } catch (error) {
            addLog(`Drafting failed for ${contact.hr_name}: ${error.message}`, 'error');
            failedCountNum++;
            currentIndex++;
            processNextContact();
        }
    }

    function displayDraft(draft) {
        editRecipient.value = draft.email;
        editSubject.value = draft.subject;
        editBody.value = draft.body;
        
        skipBtn.disabled = false;
        approveBtn.disabled = false;
        
        addLog(`Draft ready for ${draft.hr_name}. Awaiting your approval.`, 'system');
    }

    approveBtn.addEventListener('click', async () => {
        skipBtn.disabled = true;
        approveBtn.disabled = true;
        
        const recipient = editRecipient.value;
        const subject = editSubject.value;
        const body = editBody.value;
        
        await sendEmail(recipient, subject, body);
    });

    skipBtn.addEventListener('click', () => {
        addLog(`Skipped contact: ${contacts[currentIndex].hr_name}`, 'dry-run');
        currentIndex++;
        clearEditor();
        processNextContact();
    });

    async function sendEmail(recipient, subject, body) {
        const isDryRun = dryRunToggle.checked;
        
        if (isDryRun) {
            addLog(`[DRY RUN] Preview generated for ${recipient}`, 'dry-run');
            successfulCountNum++;
            finishStep();
            return;
        }

        try {
            const response = await fetch('/send-approved-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipient_email: recipient,
                    subject: subject,
                    body: body
                })
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                addLog(`Email sent successfully to ${recipient}`, 'success');
                successfulCountNum++;
            } else {
                addLog(`Failed to send to ${recipient}: ${result.message}`, 'error');
                failedCountNum++;
            }
        } catch (error) {
            addLog(`Error sending to ${recipient}: ${error.message}`, 'error');
            failedCountNum++;
        }
        
        finishStep();
    }

    function finishStep() {
        currentIndex++;
        clearEditor();
        processNextContact();
    }

    function clearEditor() {
        editRecipient.value = '';
        editSubject.value = '';
        editBody.value = '';
        skipBtn.disabled = true;
        approveBtn.disabled = true;
    }

    function updateProgress() {
        const total = contacts.length;
        if (total === 0) return;

        const percentage = Math.round((currentIndex / total) * 100);
        
        progressBar.style.width = `${percentage}%`;
        percentageText.textContent = `${percentage}%`;
        progressText.textContent = currentIndex >= total ? "Completed" : `Contact ${currentIndex + 1} of ${total}`;
        
        successCount.textContent = successfulCountNum;
        failedCount.textContent = failedCountNum;
    }
});
