# Use the official Ubuntu image as the base image
FROM golang:1.21.3

# Set the working directory inside the container
WORKDIR /app

# Update the package lists and install necessary dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Copy the contents of your Go application directory into the container
COPY . .

# Build your Go application
RUN go build -tags netgo -ldflags '-s -w' -o app

# Expose the port if your Go code listens on a specific port
EXPOSE 8086

# Command to run your Go application
CMD ["./app"]
