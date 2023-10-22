package webScraper

import (
	"context"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

func ScrapeUrlWithTimeout(c *gin.Context) {
	// Create a context with a 10-second timeout
	ctx, cancel := context.WithTimeout(c, 16*time.Second)
	defer cancel()

	// Use a channel to signal when the operation is completed
	done := make(chan struct{})

	// Run the original ScrapeUrl function in a goroutine
	go func() {
		ScrapeUrl(c)
		close(done)
	}()

	// Wait for the context to be done, the operation to complete, or the timeout to occur
	select {
	case <-ctx.Done():
		if ctx.Err() == context.DeadlineExceeded {
			// Handle the timeout
			c.JSON(http.StatusRequestTimeout, gin.H{"error": "Request timed out"})
		}
	case <-done:
		// The operation completed, cancel the context
		cancel()
	case <-c.Done():
		// The client disconnected, handle as needed
		fmt.Println("Client disconnected")
	}
}

// Original ScrapeUrl function
func ScrapeUrl(c *gin.Context) {
	// Params from the request
	url := c.PostForm("url")
	proxy := c.PostForm("proxy")
	js_render := c.PostForm("js_render")
	additional_delay := c.PostForm("additional_delay")
	// parse additional_delay to int
	additional_delay_int, _ := strconv.Atoi(additional_delay)

	preConditionsStatus, err := preConditions(url, proxy, js_render, additional_delay)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
	} else if !preConditionsStatus {
		c.JSON(500, gin.H{"error": "preConditions failed"})
	} else {
		// Scrape the URL
		if js_render == "true" {
			proxyIP, proxyUser, proxyPassword := proxyDecoder(proxy)

			html, err := ScrapeJSPage(url, proxyIP, proxyUser, proxyPassword, additional_delay_int)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
			} else {
				c.JSON(200, gin.H{"html": html, "url": url})
			}
		} else {
			html, err := scrapePage(url, proxy)
			if err != nil {
				c.JSON(500, gin.H{"error": err.Error()})
			} else {
				c.JSON(200, gin.H{"html": html, "url": url})
			}
		}
	}
}
