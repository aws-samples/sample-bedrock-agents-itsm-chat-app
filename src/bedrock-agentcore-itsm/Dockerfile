FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum update -y && yum install -y gcc

# Copy requirements and install Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt

# Copy agent code
COPY agent/ ${LAMBDA_TASK_ROOT}/agent/

# Set the CMD to your handler
CMD ["agent.strands_agent.handler"]
