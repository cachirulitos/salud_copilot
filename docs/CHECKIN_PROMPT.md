# Check-in Module: Dynamic Exam Ordering

## Description

Refactor the check-in module to handle dynamic exam sequences. The Check-in entity must receive the required steps (exams) to conclude a visit. Users can change the exam sequence (e.g., X-rays before Optometry) as long as the new order strictly validates against the `packages/rules_engine`.

## Execution Constraints (SYSTEM INSTRUCTIONS - APPLY TO ALL PROMPTS)

- ENGLISH ONLY.
- STRICT TOKEN OPTIMIZATION: OUTPUT ONLY RAW CODE.
- NO conversational text, NO greetings, NO "Here is the implementation", NO summaries, NO markdown wrappers around explanations. Just the code blocks.
- Include file paths as comments at the top of each code block.

---

## Prompt 1: Entities & Interfaces

Apply the system instructions.
Update the Checkin entity, DTOs, and interfaces to support an array of `requiredExams` and their sequence order.
Define the necessary payload structures to communicate with `packages/rules_engine` for sequence validation.

---

## Prompt 2: Rules Engine Integration

Apply the system instructions.
Implement a validation service/adapter that takes a proposed exam sequence and evaluates it using `packages/rules_engine`.
It must validate if the sequence is allowed (e.g., prerequisites are met) and throw a specific domain error if the sequence violates the business rules.

---

## Prompt 3: Reorder Use Case & Controller

Apply the system instructions.
Implement the core use case (or service) and the controller endpoint that allows the user to change the order of their exams.
This use case MUST inject the validation service from Prompt 2. It should accept the new order, run the rules_engine validation, and persist the updated Checkin entity only if the rules pass.
