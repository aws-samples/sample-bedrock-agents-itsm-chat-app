# Implementation Plan: Bedrock AgentCore Migration

## Overview

This implementation plan creates a dual-deployment architecture allowing users to choose between Bedrock Agents and Bedrock AgentCore for their ITSM solution. The approach maintains the existing Bedrock Agents implementation while adding a parallel AgentCore implementation that provides identical functionality through a different deployment model.

## Tasks

- [x] 1. Set up AgentCore directory structure and core configuration
  - Create `src/bedrock-agentcore/` directory structure
  - Set up basic project files (README, requirements.txt)
  - Create CloudFormation template structure for AgentCore
  - _Requirements: 2.1, 6.1_

- [x] 1.1 Write property test for directory structure validation
  - **Property 7: Naming Convention Consistency**
  - **Validates: Requirements 6.4**

- [x] 2. Implement shared ITSM Lambda functions for AgentCore
  - [x] 2.1 Copy and adapt create-itsm Lambda function for AgentCore use
    - Copy existing `src/bedrock-agent-itsm/functions/create-itsm/index.js`
    - Adapt for AgentCore directory structure
    - Ensure identical DynamoDB operations
    - _Requirements: 2.2, 3.3_

  - [x] 2.2 Copy and adapt lookup-itsm Lambda function for AgentCore use
    - Copy existing `src/bedrock-agent-itsm/functions/lookup-itsm/index.js`
    - Adapt for AgentCore directory structure
    - Ensure identical DynamoDB operations
    - _Requirements: 2.3, 3.3_

- [x] 2.3 Write property tests for ITSM function equivalence
  - **Property 1: Functional Equivalence Across Implementations**
  - **Validates: Requirements 2.2, 2.3**

- [x] 3. Create AgentCore agent implementation using Strands framework
  - [x] 3.1 Implement main Strands agent class
    - Create `src/bedrock-agentcore/agent/strands_agent.py`
    - Implement agent orchestration logic
    - Configure agent with proper instructions and model
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 3.2 Implement CreateTicketTool
    - Create `src/bedrock-agentcore/agent/tools/create_ticket.py`
    - Implement API Gateway integration for ticket creation
    - Ensure identical request/response format to Bedrock Agents
    - _Requirements: 2.2, 2.5_

  - [x] 3.3 Implement LookupTicketTool
    - Create `src/bedrock-agentcore/agent/tools/lookup_ticket.py`
    - Implement API Gateway integration for ticket lookup
    - Ensure identical request/response format to Bedrock Agents
    - _Requirements: 2.3, 2.5_

  - [x] 3.4 Implement KnowledgeBaseTool
    - Create `src/bedrock-agentcore/agent/tools/knowledge_base.py`
    - Implement Bedrock Runtime API integration for knowledge base queries
    - Ensure equivalent functionality to Bedrock Agents knowledge base
    - _Requirements: 2.4_

- [x] 3.5 Write property tests for agent tool functionality
  - **Property 2: API Interface Consistency**
  - **Validates: Requirements 2.5, 4.5**

- [x] 4. Create AgentCore CloudFormation template
  - [x] 4.1 Implement shared infrastructure resources
    - Copy DynamoDB table definition from existing template
    - Copy S3 bucket and OpenSearch configuration
    - Copy API Gateway definition
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 4.2 Implement AgentCore Runtime resources
    - Add `AWS::BedrockAgentCore::Runtime` resource
    - Configure container settings and execution role
    - Set up runtime endpoint configuration
    - _Requirements: 3.1, 3.2_

  - [x] 4.3 Implement IAM roles and policies for AgentCore
    - Create execution role for AgentCore Runtime
    - Configure permissions for DynamoDB, S3, OpenSearch access
    - Ensure equivalent permissions to Bedrock Agents implementation
    - _Requirements: 3.5_

- [x] 4.4 Write property tests for infrastructure compatibility
  - **Property 3: Infrastructure Resource Compatibility**
  - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

- [x] 5. Checkpoint - Ensure core AgentCore implementation works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement deployment and configuration management
  - [x] 6.1 Create AgentCore deployment scripts
    - Create deployment script using bedrock-agentcore-starter-toolkit
    - Configure automatic container building and deployment
    - Set up environment variable management
    - _Requirements: 5.1_

  - [x] 6.2 Create deployment validation logic
    - Implement AWS service availability checks
    - Validate required permissions before deployment
    - Create pre-deployment validation script
    - _Requirements: 5.3_

- [x] 6.3 Write property tests for deployment validation
  - **Property 5: Deployment Validation**
  - **Validates: Requirements 5.3**

- [x] 7. Implement data consistency and migration support
  - [x] 7.1 Create data format validation utilities
    - Implement ticket data format validation
    - Create data consistency checking functions
    - Ensure both implementations use identical data schemas
    - _Requirements: 4.1, 4.2_

  - [x] 7.2 Implement migration testing utilities
    - Create scripts to test implementation switching
    - Implement data preservation validation
    - Create rollback testing procedures
    - _Requirements: 5.5_

- [x] 7.3 Write property tests for data consistency
  - **Property 4: Data Consistency and Format Equivalence**
  - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

- [x] 7.4 Write property tests for migration data preservation
  - **Property 6: Migration Data Preservation**
  - **Validates: Requirements 5.5**

- [x] 8. Create documentation and README files
  - [x] 8.1 Create AgentCore implementation README
    - Document AgentCore architecture and components
    - Provide deployment instructions
    - Explain differences from Bedrock Agents approach
    - _Requirements: 1.5, 6.5_

  - [x] 8.2 Create deployment choice documentation
    - Document when to choose Bedrock Agents vs AgentCore
    - Provide comparison of features and capabilities
    - Include migration procedures between implementations
    - _Requirements: 1.5, 5.2_

  - [x] 8.3 Update root README with dual implementation information
    - Update main project README to explain both options
    - Provide quick start guides for both implementations
    - Include architecture diagrams
    - _Requirements: 1.5_

- [x] 9. Integration testing and validation
  - [x] 9.1 Test chat frontend integration with AgentCore
    - Verify chat-app works identically with AgentCore backend
    - Test all ITSM operations through the frontend
    - Validate error handling and response formats
    - _Requirements: 1.4, 4.5_

  - [x] 9.2 Test cross-implementation data compatibility
    - Create tickets with Bedrock Agents, read with AgentCore
    - Create tickets with AgentCore, read with Bedrock Agents
    - Verify knowledge base queries work identically
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 9.3 Write integration tests for frontend compatibility
  - Test chat frontend works with both implementations
  - Verify API response formats are identical
  - _Requirements: 1.4, 4.5_

- [x] 10. Final checkpoint and deployment validation
  - Ensure all tests pass, ask the user if questions arise.
  - Validate both implementations can be deployed independently
  - Verify shared resources work correctly with both implementations

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains the existing Bedrock Agents code unchanged
- AgentCore implementation uses Python (Strands framework) for the agent and JavaScript for shared Lambda functions