package main

import (
	"github.com/gin-gonic/gin"
	webScraper "scrape-n.com/apis/functions"
)

func main() {
	r := gin.Default()
	// Auth middleware
	// r.Use(authMiddleware())

	r.POST("/scrape", webScraper.ScrapeUrlWithTimeout)

	r.Run(":8080") // listen and serve on
}

// To Build:
// go build -tags netgo -ldflags '-s -w' -o app

// To Run:
// ./app

// Each build param explained:
// -tags netgo: This tells the Go compiler to use the netgo network implementation, which uses the pure Go DNS resolver.
// -ldflags '-s -w': This tells the Go compiler to omit the symbol table and debug information from the executable.
// -o app: This tells the Go compiler to name the executable app.
