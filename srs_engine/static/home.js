document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("srsForm");

    // Show/hide custom input for Target Users
    const targetUsersOtherCheck = document.getElementById("target_users_other_check");
    const targetUsersCustomInput = document.getElementById("target_users_custom");

    if (targetUsersOtherCheck) {
        targetUsersOtherCheck.addEventListener("change", (e) => {
            if (e.target.checked) {
                targetUsersCustomInput.style.display = "block";
            } else {
                targetUsersCustomInput.style.display = "none";
                targetUsersCustomInput.value = "";
            }
        });
    }

    // Show/hide custom input for Domain
    const domainSelect = document.getElementById("domain");
    const domainCustomInput = document.getElementById("domain_custom");

    if (domainSelect) {
        domainSelect.addEventListener("change", (e) => {
            // Domain info display is now handled by domain-data.js
            // Only show/hide custom input here
            if (e.target.value === "Other") {
                domainCustomInput.style.display = "block";
            } else {
                domainCustomInput.style.display = "none";
                domainCustomInput.value = "";
            }
        });
    }

    // Show/hide custom input for Compliance
    const complianceOtherCheck = document.getElementById("compliance_other_check");
    const complianceCustomInput = document.getElementById("compliance_custom");

    if (complianceOtherCheck) {
        complianceOtherCheck.addEventListener("change", (e) => {
            if (e.target.checked) {
                complianceCustomInput.style.display = "block";
            } else {
                complianceCustomInput.style.display = "none";
                complianceCustomInput.value = "";
            }
        });
    }

    // ========== AUTO-GENERATE FUNCTIONALITY ==========
    const autoGenerateFeaturesBtn = document.getElementById("autoGenerateFeaturesBtn");
    const autoGenerateFlowBtn = document.getElementById("autoGenerateFlowBtn");
    const enhanceProblemBtn = document.getElementById("enhanceProblemBtn");
    const featuresStatus = document.getElementById("featuresStatus");
    const flowStatus = document.getElementById("flowStatus");
    const problemStatus = document.getElementById("problemStatus");
    const projectNameInput = document.getElementById("project_name");
    const problemStatementInput = document.getElementById("problem_statement");
    const coreFeaturesTextarea = document.getElementById("core_features");
    const primaryUserFlowTextarea = document.getElementById("primary_user_flow");

    // Function to check if auto-generate buttons should be enabled
    const checkAutoGenerateEnabled = () => {
        const projectName = projectNameInput.value.trim();
        const problemStatement = problemStatementInput.value.trim();
        
        const isEnabled = projectName && problemStatement;
        
        // Enable/disable auto-generate buttons
        autoGenerateFeaturesBtn.disabled = !isEnabled;
        autoGenerateFlowBtn.disabled = !isEnabled;
        
        autoGenerateFeaturesBtn.style.opacity = isEnabled ? "1" : "0.5";
        autoGenerateFlowBtn.style.opacity = isEnabled ? "1" : "0.5";
        
        // Enable/disable enhance button (only needs project name and problem statement)
        const enhanceEnabled = projectName && problemStatement;
        enhanceProblemBtn.disabled = !enhanceEnabled;
        enhanceProblemBtn.style.opacity = enhanceEnabled ? "1" : "0.5";
    };

    // Listen to changes on required fields
    projectNameInput.addEventListener("input", checkAutoGenerateEnabled);
    problemStatementInput.addEventListener("input", checkAutoGenerateEnabled);

    // Generic function to handle auto-generation
    const handleAutoGenerate = async (type, button, statusDiv, textarea) => {
        const projectName = projectNameInput.value.trim();
        const problemStatement = problemStatementInput.value.trim();

        if (!projectName || !problemStatement) {
            alert("Please fill in Project Name and Problem Statement first.");
            return;
        }

        // Disable button and show loading state
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "⏳ Generating...";
        statusDiv.textContent = "Generating...";
        statusDiv.style.color = "#0066cc";

        const payload = {
            
            project_name: projectName,
            problem_statement: problemStatement,
            section_type: type // "features" or "flow"
        };

        try {
            const response = await fetch("/auto-generate-section", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log(`Auto-generate ${type} response:`, result);

            // Populate the textarea with the generated content
            if (type === "features") {
                // Handle both direct and nested response formats
                let coreFeatures = result.core_features || result;
                
                if (typeof coreFeatures === 'string') {
                    // If it's a JSON string, parse it
                    try {
                        const parsed = JSON.parse(coreFeatures);
                        coreFeatures = parsed.core_features || parsed;
                    } catch (e) {
                        // If parsing fails, use as-is
                    }
                }
                
                if (Array.isArray(coreFeatures)) {
                    textarea.value = coreFeatures.join("\n");
                    statusDiv.textContent = "✅ Generated successfully!";
                } else if (typeof coreFeatures === 'object' && coreFeatures.core_features) {
                    textarea.value = coreFeatures.core_features.join("\n");
                    statusDiv.textContent = "✅ Generated successfully!";
                } else {
                    throw new Error("Invalid response format for features");
                }
            } else if (type === "flow") {
                // Handle both direct and nested response formats
                let userFlow = result.primary_user_flow || result;
                
                if (typeof userFlow === 'object' && userFlow.primary_user_flow) {
                    userFlow = userFlow.primary_user_flow;
                }
                
                if (typeof userFlow === 'string' && userFlow.length > 0) {
                    textarea.value = userFlow;
                    statusDiv.textContent = "✅ Generated successfully!";
                } else {
                    throw new Error("Invalid response format for user flow");
                }
            } else {
                throw new Error("Invalid response format");
            }

            statusDiv.style.color = "#28a745";

            // Reset button and clear status after 2 seconds
            setTimeout(() => {
                button.textContent = originalText;
                button.disabled = false;
                statusDiv.textContent = "";
                checkAutoGenerateEnabled(); // Re-check in case inputs changed
            }, 2000);

        } catch (error) {
            console.error(`Auto-generate ${type} error:`, error);
            statusDiv.textContent = `❌ Error: ${error.message}`;
            statusDiv.style.color = "#dc3545";
            
            // Reset button
            button.textContent = originalText;
            button.disabled = false;
            checkAutoGenerateEnabled();
        }
    };

    // Auto-generate Features button click handler
    autoGenerateFeaturesBtn.addEventListener("click", () => {
        handleAutoGenerate("features", autoGenerateFeaturesBtn, featuresStatus, coreFeaturesTextarea);
    });

    // Auto-generate Flow button click handler
    autoGenerateFlowBtn.addEventListener("click", () => {
        handleAutoGenerate("flow", autoGenerateFlowBtn, flowStatus, primaryUserFlowTextarea);
    });

    // Enhance Problem Statement button click handler
    enhanceProblemBtn.addEventListener("click", async () => {
        const projectName = projectNameInput.value.trim();
        const problemStatement = problemStatementInput.value.trim();

        if (!projectName || !problemStatement) {
            alert("Please fill in Project Name and Problem Statement first.");
            return;
        }

        // Disable button and show loading state
        const originalText = enhanceProblemBtn.textContent;
        enhanceProblemBtn.disabled = true;
        enhanceProblemBtn.textContent = "⏳ Enhancing...";
        problemStatus.textContent = "Enhancing problem statement...";
        problemStatus.style.color = "#0066cc";

        const payload = {
            project_name: projectName,
            problem_statement: problemStatement
        };

        try {
            const response = await fetch("/enhance-problem-statement", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log("Enhance problem response:", result);

            // Update the problem statement textarea with enhanced version
            if (result.enhanced_problem_statement) {
                problemStatementInput.value = result.enhanced_problem_statement;
                problemStatus.textContent = "✅ Problem statement enhanced!";
                problemStatus.style.color = "#28a745";
            } else {
                throw new Error("Invalid response format");
            }

            // Reset button and clear status after 3 seconds
            setTimeout(() => {
                enhanceProblemBtn.textContent = originalText;
                enhanceProblemBtn.disabled = false;
                problemStatus.textContent = "";
                checkAutoGenerateEnabled();
            }, 3000);

        } catch (error) {
            console.error("Enhance problem error:", error);
            problemStatus.textContent = `❌ Error: ${error.message}`;
            problemStatus.style.color = "#dc3545";
            
            // Reset button
            enhanceProblemBtn.textContent = originalText;
            enhanceProblemBtn.disabled = false;
            checkAutoGenerateEnabled();
        }
    });

    // Initial check on page load
    checkAutoGenerateEnabled();

    // ========== FORM SUBMISSION HANDLER ==========
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const formData = new FormData(form);

        // ---------- Helper Functions ----------
        const getCheckedValues = (name) =>
            Array.from(document.querySelectorAll(`input[name="${name}"]:checked`))
                .map(el => el.value)
                .filter(val => val !== "Other"); // Exclude "Other" from the array

        const splitToArray = (value) =>
            value
                ? value.split(/[\n,]/).map(v => v.trim()).filter(Boolean)
                : [];

        // ---------- Target Users ----------
        let targetUsers = getCheckedValues("target_users");
        const customUser = document.getElementById("target_users_custom")?.value.trim();
        if (customUser) {
            targetUsers.push(customUser);
        }

        // Validate at least one target user
        if (targetUsers.length === 0) {
            alert("Please select at least one target user");
            return;
        }

        // ---------- Domain ----------
        let domain = formData.get("domain");
        
        // If "Other" is selected, check if custom domain is provided
        // If no custom domain, use "Other" as the domain value
        if (domain === "Other") {
            const customDomain = document.getElementById("domain_custom")?.value.trim();
            if (customDomain) {
                domain = customDomain; // Use custom domain name if provided
            }
            // Otherwise keep domain as "Other" - it's valid
        }

        // ---------- Compliance ----------
        let compliance = getCheckedValues("compliance_requirements");
        const customCompliance = document.getElementById("compliance_custom")?.value.trim();
        if (customCompliance) {
            compliance.push(customCompliance);
        }

        // If no compliance requirements selected, use empty array
        if (compliance.length === 0) {
            compliance = [];
        }

        // ---------- Authors ----------
        const author = splitToArray(formData.get("author"));
        if (author.length === 0) {
            alert("Please provide at least one author name");
            return;
        }

        // ---------- Core Features ----------
        const coreFeatures = splitToArray(formData.get("core_features"));
        if (coreFeatures.length === 0) {
            alert("Please provide at least one core feature");
            return;
        }

        // ---------- Booleans ----------
        const authenticationRequired = formData.get("authentication_required") === "true";
        const sensitiveDataHandling = formData.get("sensitive_data_handling") === "true";

        // ---------- FINAL PAYLOAD ----------
        const payload = {
            project_identity: {
                project_name: formData.get("project_name").trim(),
                author: author,
                organization: formData.get("organization").trim(),
                problem_statement: formData.get("problem_statement").trim(),
                target_users: targetUsers
            },

            system_context: {
                application_type: formData.get("application_type"),
                domain: domain
            },

            functional_scope: {
                core_features: coreFeatures,
                primary_user_flow: formData.get("primary_user_flow")?.trim() || null
            },

            non_functional_requirements: {
                expected_user_scale: formData.get("expected_user_scale"),
                performance_expectation: formData.get("performance_expectation")
            },

            security_and_compliance: {
                authentication_required: authenticationRequired,
                sensitive_data_handling: sensitiveDataHandling,
                compliance_requirements: compliance
            },

            technical_preferences: {
                preferred_backend: formData.get("preferred_backend")?.trim() || null,
                database_preference: formData.get("database_preference")?.trim() || null,
                deployment_preference: formData.get("deployment_preference")?.trim() || null
            },

            output_control: {
                srs_detail_level: formData.get("srs_detail_level")
            }
        };

        console.log("SRS Payload:", JSON.stringify(payload, null, 2));

        // ---------- SEND TO BACKEND ----------
        try {
            const response = await fetch("/generate_srs", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error("Server error:", errorText);
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log("Server response:", result);
            alert("SRS generated successfully!");

        } catch (error) {
            console.error("Submission error:", error);
            alert(`Failed to generate SRS: ${error.message}`);
        }
    });
});