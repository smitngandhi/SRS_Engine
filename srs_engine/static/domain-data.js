/**
 * domain-data.js
 * Comprehensive domain data for SRS_Engine — all 8 domains + General.
 * Each domain contains: standards, sections (with what/why/includes),
 * and a short one-liner per standard for tooltip display.
 */

const domainData = {

  Healthcare: {
    title: "Healthcare & Medical Devices",
    color: "#4f8eff",
    icon: "🏥",
    standards: ["IEC 62304", "FDA 21 CFR Part 820", "ISO 13485", "ISO 14971", "HIPAA", "HL7", "FHIR", "DICOM"],
    standardDescriptions: {
      "IEC 62304":         "Defines how medical device software must be developed, documented, tested, and maintained safely throughout its lifecycle.",
      "FDA 21 CFR Part 820": "U.S. law requiring medical device manufacturers to follow documented quality and design control procedures including testing and traceability.",
      "ISO 13485":         "International quality management system standard ensuring medical devices are produced consistently with documented, auditable processes.",
      "ISO 14971":         "Framework to identify, evaluate, control, and monitor risks associated with medical devices to keep patients and users safe.",
      "HIPAA":             "U.S. regulation protecting patient health information privacy and security in electronic systems.",
      "HL7":               "Messaging standards for interoperability between healthcare information systems.",
      "FHIR":              "Modern REST-based API standard for exchanging healthcare information electronically.",
      "DICOM":             "Standard for medical imaging data storage, transmission, and display."
    },
    sections: [
      {
        number: "1",
        title: "Introduction & Purpose",
        subsections: [
          { id: "1.1", title: "Document Scope", what: "Context and boundaries of the SRS — which software it covers, what it does and doesn't include.", why: "Helps auditors and reviewers understand what parts of the product the SRS applies to so requirements aren't misinterpreted.", includes: ["Overview of the software and its role", "Targeted users", "System where it is integrated", "High-level product description"] },
          { id: "1.2", title: "Regulatory & Standards References", what: "List of applicable standards/regulations (IEC 62304, ISO 14971, FDA, GDPR/HIPAA if relevant).", why: "Shows what compliance framework this SRS follows — regulators expect this list.", includes: ["Regulatory standards and versions", "Internal QMS SOP references", "Design control procedures"] },
          { id: "1.3", title: "Acronyms, Definitions & Abbreviations", what: "Glossary to ensure all stakeholders interpret terms consistently.", why: "SRS must be unambiguous; glossaries reduce miscommunication.", includes: [] },
          { id: "1.4", title: "Intended Use & Indications", what: "Describes why the device exists and how it should be used clinically.", why: "Regulatory submissions require clear intended use. It determines risk analyses and classification.", includes: [] },
          { id: "1.5", title: "Target Population & Environment", what: "Patient types, clinical settings, user profiles (clinician, nurse, patient).", why: "Affects usability and risk analysis. Regulators assess whether environment impacts safety.", includes: [] }
        ]
      },
      { number: "2", title: "Software Safety Classification", what: "The software safety class per IEC 62304 (Class A, B, or C).", why: "Determines the rigor of processes and testing required. Higher classes require more documentation & testing.", includes: ["Class assigned", "Rationale for classification"], subsections: [] },
      {
        number: "3", title: "System Overview & Description",
        subsections: [
          { id: "3.1", title: "Product Perspective", what: "How the medical software fits into the larger system.", why: "Helps linkage between system requirements and software requirements.", includes: [] },
          { id: "3.2", title: "System Functions", what: "Big-picture functions the software must perform (monitoring, reporting, control).", why: "Forms basis of detailed software requirements later.", includes: [] },
          { id: "3.3", title: "Operational Environment & Constraints", what: "Hardware, network, regulatory compliance dependencies, performance limitations.", why: "Requirements often depend on where the software runs.", includes: [] }
        ]
      },
      {
        number: "4", title: "Requirements Specification",
        subsections: [
          { id: "4.1", title: "Functional Requirements", what: "Clear, testable actions the software must do.", why: "IEC 62304 requires functional requirements that tie to design and testing.", includes: ['\"The system shall record vital signs every second.\"', '\"The system shall trigger alert if value > threshold.\"'] },
          { id: "4.2", title: "Performance & Reliability Requirements", what: "Response time, accuracy, uptime, performance targets.", why: "Performance expectations must be verified and related to risk.", includes: [] },
          { id: "4.3", title: "Interface Requirements", what: "How software connects with users, devices, EMRs, external systems.", why: "Regulatory reviewers assess interface correctness — ambiguous interfaces cause failures.", includes: ["User interface", "APIs", "Communication standards (HL7, FHIR, DICOM)"] },
          { id: "4.4", title: "Data Security & Privacy", what: "Handling of PHI/PII under HIPAA/GDPR etc.", why: "Modern healthcare data requires documented privacy controls.", includes: [] },
          { id: "4.5", title: "Safety & Risk Control Requirements", what: "Software controls that mitigate risks found in risk analysis.", why: "ISO 14971 requires risk controls be designed into the requirements and verified later.", includes: [] }
        ]
      },
      {
        number: "5", title: "Software Architecture Description",
        subsections: [
          { id: "5.1", title: "Architecture Overview", what: "Block diagrams, modules, components.", why: "Shows how requirements flow through software structure.", includes: [] },
          { id: "5.2", title: "Interfaces Between Components", what: "Interfaces, data flows.", why: "Needed for hazard analysis and design completeness.", includes: [] },
          { id: "5.3", title: "Segregation & Risk Control", what: "Isolation of safety-critical parts, partitions.", why: "Demonstrates risk containment per IEC 62304.", includes: [] }
        ]
      },
      {
        number: "6", title: "Hazard & Risk Analysis Results",
        subsections: [
          { id: "6.1", title: "Hazard Identification", what: "List of hazards from analysis.", why: "ISO 14971 requires identification and documentation of hazards.", includes: [] },
          { id: "6.2", title: "Risk Control Measures", what: "How requirements reduce risk.", why: "Must link requirements directly to mitigation.", includes: [] },
          { id: "6.3", title: "SOUP/OTS Analysis", what: "Documentation of third-party software risks and controls.", why: "FDA and IEC 62304 expect SOUP risk evaluation and controls.", includes: [] }
        ]
      },
      {
        number: "7", title: "Verification & Validation Planning",
        subsections: [
          { id: "7.1", title: "Test Scope", what: "Types of tests planned (unit, integration, system, validation).", why: "FDA design controls require documented V&V.", includes: [] },
          { id: "7.2", title: "Acceptance Criteria", what: "Pass/fail criteria for requirements.", why: "Test plans must be measurable and objective.", includes: [] },
          { id: "7.3", title: "Test Methods & Protocols", what: "How each requirement will be tested.", why: "Traceability to verification is regulatory requirement.", includes: [] }
        ]
      },
      { number: "8", title: "Traceability Matrix", what: "Mapping of requirements → design elements → risk controls → tests.", why: "Regulators expect evidence linking requirements to risk and tests.", includes: [], subsections: [] },
      { number: "9", title: "Appendices", what: "References to SOPs, other documents (DHF, SDS).", why: "Helps evidence continuity and completeness.", includes: [], subsections: [] }
    ],
    note: "Your SRS will include medical device-specific requirements following IEC 62304 standards with proper risk classification and safety requirements."
  },

  Finance: {
    title: "Financial Services & Fintech",
    color: "#00e5c9",
    icon: "💳",
    standards: ["PCI DSS", "SOX", "GDPR", "CCPA", "GLBA", "BSA", "Dodd-Frank", "KYC", "AML", "OFAC"],
    standardDescriptions: {
      "PCI DSS":     "Payment Card Industry Data Security Standard — security controls for processing, storing, or transmitting card data.",
      "SOX":         "Sarbanes-Oxley Act requiring auditability and integrity of financial data systems.",
      "GDPR":        "EU regulation on personal data protection and privacy.",
      "CCPA":        "California Consumer Privacy Act — rights for California residents over their personal data.",
      "GLBA":        "Gramm-Leach-Bliley Act requiring financial institutions to protect consumer financial information.",
      "BSA":         "Bank Secrecy Act requiring financial institutions to assist government in detecting money laundering.",
      "Dodd-Frank":  "U.S. financial reform law with sweeping regulatory requirements post-2008 crisis.",
      "KYC":         "Know Your Customer — identity verification processes for financial customers.",
      "AML":         "Anti-Money Laundering — controls to detect and prevent laundering of illicit funds.",
      "OFAC":        "Office of Foreign Assets Control — sanctions and embargo compliance requirements."
    },
    sections: [
      { number: "1", title: "Introduction & Scope", includes: ["Financial service type (payments, lending, investment, banking)", "Regulatory jurisdiction (US, EU, APAC)", "License requirements (MTL, RIA, Broker-Dealer)"], subsections: [] },
      { number: "2", title: "Regulatory Compliance Requirements", includes: ["Anti-Money Laundering (AML) controls", "Know Your Customer (KYC) verification", "Counter-Terrorism Financing (CTF) measures", "OFAC and sanctions screening", "Bank Secrecy Act (BSA) compliance", "Fair lending practices (TILA, FCRA)"], subsections: [] },
      { number: "3", title: "Security & Data Protection", includes: ["PCI DSS compliance for payment card data", "GDPR compliance for EU data", "CCPA compliance for California residents", "Encryption standards (data at rest and in transit)", "Secure authentication mechanisms", "Multi-factor authentication (MFA)"], subsections: [] },
      { number: "4", title: "Transaction Processing Requirements", includes: ["Payment processing specifications", "ACH and wire transfer capabilities", "Real-time payment processing", "Transaction monitoring and fraud detection", "Settlement and reconciliation processes"], subsections: [] },
      { number: "5", title: "Reporting & Audit Requirements", includes: ["Suspicious Activity Reports (SAR)", "Currency Transaction Reports (CTR)", "Regulatory reporting to CFPB, SEC, FINRA", "Audit trail and logging requirements", "Financial disclosure requirements"], subsections: [] },
      { number: "6", title: "Risk Management Requirements", includes: ["Credit risk assessment", "Operational risk controls", "Market risk management", "Cybersecurity risk assessment (FFIEC guidelines)", "Third-party risk management"], subsections: [] },
      { number: "7", title: "Business Continuity & Disaster Recovery", includes: ["Backup and recovery procedures", "Failover mechanisms", "Data retention policies", "Incident response procedures"], subsections: [] }
    ],
    note: "Your SRS will include financial regulatory compliance requirements for payment processing, data security, and audit trails."
  },

  Aerospace: {
    title: "Aerospace & Aviation",
    color: "#a78bfa",
    icon: "✈️",
    standards: ["DO-178C/ED-12C", "DO-330", "ARP4754A", "DO-254", "ASIL/DAL Classification"],
    standardDescriptions: {
      "DO-178C/ED-12C":       "Primary standard for airborne software development — defines processes for all design assurance levels.",
      "DO-330":               "Tool qualification standard ensuring development tools used meet safety criteria.",
      "ARP4754A":             "Guidelines for development of civil aircraft and systems including hardware-software integration.",
      "DO-254":               "Design assurance guidance for airborne electronic hardware.",
      "ASIL/DAL Classification": "Design Assurance Level classification (A-E) determining rigor of verification and documentation."
    },
    sections: [
      { number: "1", title: "Introduction & Certification Basis", includes: ["Aircraft system description", "Software level classification (Level A-E / DAL)", "ASIL determination (Catastrophic, Hazardous, Major, Minor, No Effect)", "Certification authority approval basis"], subsections: [] },
      { number: "2", title: "Plan for Software Aspects of Certification (PSAC)", includes: ["Software development approach", "Certification liaison process", "Stages of Involvement (SOI)"], subsections: [] },
      { number: "3", title: "Software Development Plan", includes: ["Development environment and tools", "Standards to be followed", "Development lifecycle model"], subsections: [] },
      { number: "4", title: "Software Verification Plan", includes: ["Verification methods and procedures", "Requirements-based testing", "Structural coverage analysis (Statement, Decision, MC/DC)", "Robustness testing", "Independence criteria"], subsections: [] },
      { number: "5", title: "Software Configuration Management Plan", includes: ["Configuration identification", "Baseline control", "Change control procedures", "Version control mechanisms"], subsections: [] },
      { number: "6", title: "Software Quality Assurance Plan", includes: ["Quality assurance activities", "Audits and reviews", "Problem reporting procedures", "Conformance review process"], subsections: [] },
      { number: "7", title: "Software Requirements Specification", includes: ["High-level requirements", "Low-level requirements", "Derived requirements", "Safety requirements (marked/tagged)", "Interface requirements"], subsections: [] },
      { number: "8", title: "Software Architecture", includes: ["Software architecture design", "Partitioning strategy", "Inter-partition communication"], subsections: [] },
      { number: "9", title: "Tool Qualification (DO-330)", includes: ["Tool qualification levels (TQL-1 to TQL-5)", "Tool operational requirements", "Tool verification procedures"], subsections: [] },
      { number: "10", title: "Bidirectional Traceability", includes: ["System requirements to software requirements", "Requirements to design", "Design to code", "Requirements to test cases"], subsections: [] }
    ],
    note: "Your SRS will follow DO-178C standards with appropriate Design Assurance Level (DAL) classification and certification requirements."
  },

  Automotive: {
    title: "Automotive",
    color: "#f59e0b",
    icon: "🚗",
    standards: ["ISO 26262", "ASPICE", "ISO 21434", "MISRA", "AUTOSAR", "ASIL Classification"],
    standardDescriptions: {
      "ISO 26262":         "Functional safety standard for road vehicles — covers entire lifecycle of safety-critical electrical/electronic systems.",
      "ASPICE":            "Automotive SPICE — process assessment model for software development capability in automotive.",
      "ISO 21434":         "Cybersecurity engineering standard for road vehicles — covers threat analysis and risk assessment.",
      "MISRA":             "Coding guidelines for safety-critical C/C++ software in automotive systems.",
      "AUTOSAR":           "Standardized software architecture for automotive ECUs enabling portability and reuse.",
      "ASIL Classification": "Automotive Safety Integrity Level (A-D) — determines required rigor of safety measures."
    },
    sections: [
      { number: "1", title: "Introduction & Scope", includes: ["Vehicle system description", "E/E system overview", "Software classification"], subsections: [] },
      { number: "2", title: "Functional Safety Concept (ISO 26262)", includes: ["Hazard Analysis and Risk Assessment (HARA)", "Automotive Safety Integrity Level (ASIL A-D)", "Safety goals", "Functional safety requirements", "Technical safety requirements"], subsections: [] },
      { number: "3", title: "System Requirements", includes: ["System functional requirements", "System non-functional requirements", "Hardware-software interface requirements", "AUTOSAR architecture compliance"], subsections: [] },
      { number: "4", title: "Software Safety Requirements", includes: ["Software safety requirements derived from system requirements", "ASIL decomposition", "Freedom from interference requirements"], subsections: [] },
      { number: "5", title: "Software Architecture Design (AUTOSAR)", includes: ["Software component architecture", "AUTOSAR software components (SWC)", "Basic software (BSW) modules", "Runtime environment (RTE)", "Communication matrix"], subsections: [] },
      { number: "6", title: "Cybersecurity Requirements (ISO 21434)", includes: ["Threat analysis and risk assessment (TARA)", "Cybersecurity goals", "Cybersecurity requirements", "Secure communication requirements"], subsections: [] },
      { number: "7", title: "ASPICE Process Requirements", includes: ["Requirements analysis (SWE.1)", "Software architectural design (SWE.2)", "Software detailed design (SWE.3)", "Software unit verification (SWE.4)", "Software integration test (SWE.5)", "Software qualification test (SWE.6)"], subsections: [] },
      { number: "8", title: "Verification & Validation", includes: ["Unit testing requirements", "Integration testing requirements", "System testing requirements", "Code coverage requirements (Statement, Branch, MC/DC based on ASIL)", "Requirements traceability"], subsections: [] },
      { number: "9", title: "Coding Standards Compliance", includes: ["MISRA C/C++ compliance", "AUTOSAR C++14 guidelines", "CERT coding standards"], subsections: [] }
    ],
    note: "Your SRS will include automotive functional safety requirements with ASIL classification and AUTOSAR compliance."
  },

  Telecom: {
    title: "Telecommunications",
    color: "#06b6d4",
    icon: "📡",
    standards: ["3GPP", "ETSI", "ITU-T", "IETF RFCs", "5G NR", "IMS"],
    standardDescriptions: {
      "3GPP":      "3rd Generation Partnership Project — defines cellular standards including 4G LTE and 5G NR.",
      "ETSI":      "European Telecommunications Standards Institute — produces globally applicable standards.",
      "ITU-T":     "ITU Telecommunication Standardization Sector — international telecom standards body.",
      "IETF RFCs": "Internet Engineering Task Force Request for Comments — internet protocol standards.",
      "5G NR":     "5G New Radio — the air interface standard for 5G mobile networks.",
      "IMS":       "IP Multimedia Subsystem — architecture for multimedia services over IP networks."
    },
    sections: [
      { number: "1", title: "Introduction & Network Context", includes: ["Network generation (2G/3G/4G/5G)", "3GPP release compliance (e.g., Release 15, 16, 17, 18)", "Network element type (RAN, Core, IMS)", "Deployment scenario (Public/Non-public networks)"], subsections: [] },
      { number: "2", title: "3GPP Specification Compliance", includes: ["Stage 1 specifications (service requirements)", "Stage 2 specifications (architecture and functional)", "Stage 3 specifications (protocol implementation)", "Relevant TS series (23.xxx, 38.xxx for 5G NR)"], subsections: [] },
      { number: "3", title: "Network Functions Requirements", includes: ["User plane functions", "Control plane functions", "Management plane functions", "Service-based architecture (SBA) interfaces"], subsections: [] },
      { number: "4", title: "Protocol Stack Requirements", includes: ["Physical layer specifications", "MAC, RLC, PDCP layer specifications", "RRC layer specifications", "NAS protocol requirements"], subsections: [] },
      { number: "5", title: "Interface Requirements", includes: ["External interfaces (N1, N2, N3, N4 for 5G)", "Inter-node communication protocols", "Reference point specifications", "API specifications (REST, SOAP)"], subsections: [] },
      { number: "6", title: "Network Management Requirements", includes: ["Configuration management", "Fault management", "Performance management", "Network slicing management (5G)", "SON capabilities"], subsections: [] },
      { number: "7", title: "Quality of Service (QoS) Requirements", includes: ["QoS flow management", "Traffic prioritization", "Latency requirements", "Throughput requirements", "Reliability targets"], subsections: [] },
      { number: "8", title: "Security Requirements", includes: ["Authentication mechanisms (5G-AKA)", "Encryption algorithms", "Integrity protection", "Lawful interception requirements", "Privacy protection"], subsections: [] },
      { number: "9", title: "Interoperability Requirements", includes: ["Multi-vendor interoperability", "Roaming capabilities", "Legacy network interworking", "Standards conformance testing"], subsections: [] }
    ],
    note: "Your SRS will follow 3GPP standards with proper network function specifications and protocol compliance."
  },

  Energy: {
    title: "Energy & Utilities",
    color: "#10b981",
    icon: "⚡",
    standards: ["NERC CIP", "FERC", "IEC 61850", "IEEE 1547", "DNP3", "Modbus"],
    standardDescriptions: {
      "NERC CIP":   "Critical Infrastructure Protection standards for bulk electric system cybersecurity.",
      "FERC":       "Federal Energy Regulatory Commission regulations for energy markets and infrastructure.",
      "IEC 61850":  "International standard for substation automation and protection communication.",
      "IEEE 1547":  "Standard for interconnection of distributed energy resources with electric power systems.",
      "DNP3":       "Distributed Network Protocol 3 — used in SCADA systems for utility automation.",
      "Modbus":     "Serial communication protocol widely used in industrial control and automation systems."
    },
    sections: [
      { number: "1", title: "Introduction & System Overview", includes: ["Utility type (Electric, Gas, Water)", "Smart grid architecture", "SCADA system integration"], subsections: [] },
      { number: "2", title: "Regulatory Compliance (NERC CIP)", includes: ["NERC CIP compliance", "FERC regulations", "Environmental compliance", "Safety standards (IEC 61850)"], subsections: [] },
      { number: "3", title: "SCADA & Control Requirements", includes: ["Real-time monitoring requirements", "Control system specifications", "Alarm management", "Historian data requirements"], subsections: [] },
      { number: "4", title: "Smart Metering Requirements (AMI)", includes: ["Meter data collection", "Demand response capabilities", "Outage detection", "Tamper detection"], subsections: [] },
      { number: "5", title: "Grid Management Requirements", includes: ["Load forecasting", "Distribution automation", "Voltage optimization", "Fault location and isolation"], subsections: [] },
      { number: "6", title: "Cybersecurity Requirements (ICS)", includes: ["NERC CIP compliance", "Industrial control system security", "Network segmentation", "Access control for critical systems"], subsections: [] },
      { number: "7", title: "Integration Requirements", includes: ["GIS integration", "Billing system integration", "Customer Information System (CIS)", "Work management system integration"], subsections: [] }
    ],
    note: "Your SRS will include critical infrastructure protection requirements and SCADA system specifications."
  },

  "E-commerce": {
    title: "E-commerce & Retail",
    color: "#f97316",
    icon: "🛒",
    standards: ["PCI DSS", "GDPR", "CCPA", "SOC 2", "ISO 27001"],
    standardDescriptions: {
      "PCI DSS":   "Payment Card Industry Data Security Standard — mandatory for any card payment processing.",
      "GDPR":      "EU data protection regulation with strict consent and privacy requirements.",
      "CCPA":      "California Consumer Privacy Act for residents' data rights.",
      "SOC 2":     "Service Organization Control 2 — audit standard for cloud and SaaS security practices.",
      "ISO 27001": "International information security management system standard."
    },
    sections: [
      { number: "1", title: "Introduction & Business Model", includes: ["Platform type (B2C, B2B, C2C, Marketplace)", "Target markets and regions"], subsections: [] },
      { number: "2", title: "User Management Requirements", includes: ["User registration and authentication", "Profile management", "Social login integration", "Multi-tenancy support"], subsections: [] },
      { number: "3", title: "Product Catalog Requirements", includes: ["Product information management", "Category and taxonomy management", "Search and filter capabilities", "Product recommendations (AI/ML)"], subsections: [] },
      { number: "4", title: "Shopping Cart & Checkout", includes: ["Cart management", "Guest checkout", "Multiple payment gateway integration", "Tax calculation", "Shipping calculation"], subsections: [] },
      { number: "5", title: "Order Management", includes: ["Order processing workflow", "Order tracking", "Return and refund management", "Inventory synchronization"], subsections: [] },
      { number: "6", title: "Payment Processing (PCI DSS)", includes: ["PCI DSS compliance", "Payment gateway integration", "Multiple currency support", "Fraud detection and prevention"], subsections: [] },
      { number: "7", title: "Inventory Management", includes: ["Real-time inventory tracking", "Multi-warehouse support", "Stock alerts", "Supplier integration"], subsections: [] },
      { number: "8", title: "Analytics & Reporting", includes: ["Sales analytics", "Customer behavior tracking", "Conversion funnel analysis", "A/B testing capabilities"], subsections: [] }
    ],
    note: "Your SRS will include e-commerce best practices with payment security and customer data protection requirements."
  },

  Education: {
    title: "Education",
    color: "#8b5cf6",
    icon: "🎓",
    standards: ["FERPA", "COPPA", "GDPR", "Section 508", "WCAG 2.1"],
    standardDescriptions: {
      "FERPA":       "Family Educational Rights and Privacy Act — protects student education records in the U.S.",
      "COPPA":       "Children's Online Privacy Protection Act — governs online collection of data from children under 13.",
      "GDPR":        "EU data protection regulation applicable when processing EU student data.",
      "Section 508": "U.S. federal law requiring accessible electronic and IT for people with disabilities.",
      "WCAG 2.1":    "Web Content Accessibility Guidelines — international standard for web accessibility."
    },
    sections: [
      { number: "1", title: "Introduction & Educational Context", includes: ["Institution type", "Learning model (online, blended, in-person)", "Target age group and user profiles"], subsections: [] },
      { number: "2", title: "Student Data Privacy (FERPA/COPPA)", includes: ["Data minimization and purpose limitation", "Parental consent mechanisms (COPPA)", "Student record access controls (FERPA)", "Data retention and deletion policies"], subsections: [] },
      { number: "3", title: "Learning Management System Requirements", includes: ["Course creation and management", "Student enrollment and tracking", "Assessment and grading", "Progress reporting"], subsections: [] },
      { number: "4", title: "Content Management & Delivery", includes: ["Multimedia content support", "Offline access capabilities", "Content versioning", "Multi-language support"], subsections: [] },
      { number: "5", title: "Assessment & Grading System", includes: ["Quiz and test creation", "Automated grading", "Anti-cheating mechanisms", "Grade reporting and transcripts"], subsections: [] },
      { number: "6", title: "Accessibility Requirements (WCAG/Section 508)", includes: ["Screen reader compatibility", "Keyboard navigation", "Color contrast compliance", "Closed captioning for media"], subsections: [] },
      { number: "7", title: "Integration Requirements (LTI/SIS)", includes: ["LTI tool integration", "Student Information System (SIS) sync", "SSO authentication", "Third-party app marketplace"], subsections: [] },
      { number: "8", title: "Analytics & Reporting", includes: ["Learning analytics dashboard", "At-risk student identification", "Instructor performance reports", "Institutional compliance reporting"], subsections: [] }
    ],
    note: "Your SRS will include educational data privacy requirements and accessibility compliance for learning systems."
  },

  Other: {
    title: "General Software Requirements Specification",
    color: "#94a3b8",
    icon: "📋",
    standards: ["IEEE 830", "ISO/IEC/IEEE 29148"],
    standardDescriptions: {
      "IEEE 830":             "Recommended practice for software requirements specifications — the foundational SRS standard.",
      "ISO/IEC/IEEE 29148":   "Supersedes IEEE 830 — international standard for requirements engineering processes and artifacts."
    },
    sections: [
      { number: "1", title: "Introduction", includes: ["Purpose and scope", "Document conventions", "Intended audience", "References"], subsections: [] },
      { number: "2", title: "Overall Description", includes: ["Product perspective", "User characteristics", "Operating environment", "Design and implementation constraints"], subsections: [] },
      { number: "3", title: "System Features / Functional Requirements", includes: ["Feature descriptions", "Use cases", "User stories", "Functional specifications"], subsections: [] },
      { number: "4", title: "External Interface Requirements", includes: ["User interfaces", "Hardware interfaces", "Software interfaces", "Communication interfaces"], subsections: [] },
      { number: "5", title: "Non-Functional Requirements", includes: ["Performance requirements", "Security requirements", "Reliability and availability", "Scalability", "Maintainability", "Usability"], subsections: [] },
      { number: "6", title: "Assumptions and Dependencies", includes: ["Technical assumptions", "Business assumptions", "External dependencies"], subsections: [] },
      { number: "7", title: "Glossary", includes: ["Domain-specific terminology", "Acronyms and abbreviations"], subsections: [] }
    ],
    note: "Your SRS will follow standard IEEE 830 / ISO 29148 format with general software engineering best practices."
  }
};

// ── Common sections present in ALL domains ────────────────
const commonSections = [
  { number: "C1", title: "Introduction", includes: ["Purpose and scope", "Document conventions", "Intended audience", "References"] },
  { number: "C2", title: "Overall Description", includes: ["Product perspective", "User characteristics", "Operating environment", "Design and implementation constraints"] },
  { number: "C3", title: "Functional Requirements", includes: ["Feature descriptions", "Use cases", "User stories", "Functional specifications"] },
  { number: "C4", title: "External Interface Requirements", includes: ["User interfaces", "Hardware interfaces", "Software interfaces", "Communication interfaces"] },
  { number: "C5", title: "Non-Functional Requirements", includes: ["Performance requirements", "Security requirements", "Reliability and availability", "Scalability", "Maintainability", "Usability"] },
  { number: "C6", title: "Assumptions and Dependencies", includes: ["Technical assumptions", "Business assumptions", "External dependencies"] },
  { number: "C7", title: "Glossary", includes: ["Domain-specific terminology", "Acronyms and abbreviations"] }
];