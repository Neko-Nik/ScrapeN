package webScraper

import (
	"errors"
	"strconv"
	"strings"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/launcher"
	"github.com/go-rod/rod/lib/launcher/flags"
	"github.com/gocolly/colly"
)

// Scrape a page that requires JavaScript to be executed with proxy authentication.
func ScrapeJSPage(url, proxyURL, proxyUsername, proxyPassword string, additionalDelay int) (string, error) {
	// Create a browser launcher and set proxy
	l := launcher.New()
	l = l.Set(flags.ProxyServer, proxyURL)

	// Connect to the newly launched browser
	controlURL, err := l.Launch()
	if err != nil {
		return "", err
	}
	browser := rod.New().ControlURL(controlURL).MustConnect()

	// Handle proxy authentication pop-up
	go browser.MustHandleAuth(proxyUsername, proxyPassword)()

	browser.MustIgnoreCertErrors(true) // Ignore certificate errors

	// Navigate to the page and wait for additional delay
	page := browser.MustPage()
	err = page.Timeout(3 * time.Second).Navigate(url)
	if err != nil {
		return "", err
	}
	page.MustWindowFullscreen()
	page.MustWaitStable()
	time.Sleep(time.Duration(additionalDelay) * time.Millisecond)

	// Extract the raw HTML from the page
	html := page.MustElement("html").MustHTML()

	return html, nil
}

// This is simple http request scraper
func scrapePage(url string, proxyURL string) (string, error) {
	c := colly.NewCollector()

	// Set up the Colly collector to use a proxy, if provided
	if proxyURL != "" {
		c.SetProxy(proxyURL)
	}

	var htmlContent string

	// Set up a callback to capture the raw HTML source
	c.OnResponse(func(r *colly.Response) {
		htmlContent = string(r.Body)
	})

	if err := c.Visit(url); err != nil {
		return "", err
	}

	return htmlContent, nil
}

// proxyDecoder - Decode the proxy string to get the username, password, ip and port
func proxyDecoder(proxyStr string) (string, string, string) {
	// the format is always http://username:password@ip:port so split it to get the username, password, ip and port
	proxyIPandPort := strings.Split(proxyStr, "@")[1]
	proxyUserandPassword := strings.Split(proxyStr, "@")[0]

	proxy := strings.Split(proxyUserandPassword, "://")[0] + "://" + proxyIPandPort
	proxyUser := strings.Split(strings.Split(proxyUserandPassword, "://")[1], ":")[0]
	proxyPassword := strings.Split(strings.Split(proxyUserandPassword, "://")[1], ":")[1]

	return proxy, proxyUser, proxyPassword
}

// preConditions - Check the preconditions for the scraper to run
func preConditions(url string, proxy string, js_render string, additional_delay string) (bool, error) {
	// check the url is not empty
	if url == "" {
		return false, errors.New("url is empty")
	} else if url[:4] != "http" {
		return false, errors.New("url should start with http or https")
	}

	// check the proxy is not empty
	if proxy == "" {
		return false, errors.New("proxy is empty")
	} else if proxyIP, proxyUser, proxyPassword := proxyDecoder(proxy); proxyIP == "" || proxyUser == "" || proxyPassword == "" {
		return false, errors.New("proxy is not in the correct format")
	}

	// check the js_render is not empty
	if js_render == "" {
		return false, errors.New("js_render is empty")
	} else if js_render != "true" && js_render != "false" {
		return false, errors.New("js_render should be true or false")
	}

	// check the additional_delay is not empty
	if additional_delay == "" {
		return false, errors.New("additional_delay is empty")
	} else if _, err := strconv.Atoi(additional_delay); err != nil {
		return false, errors.New("additional_delay should be integer")
	} else if delay, _ := strconv.Atoi(additional_delay); delay < 1000 || delay > 10000 {
		return false, errors.New("additional_delay should be between 1000 to 10000")
	}

	return true, nil
}
