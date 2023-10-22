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
