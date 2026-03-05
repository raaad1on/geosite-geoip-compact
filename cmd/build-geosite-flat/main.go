package main

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	routercommon "github.com/v2fly/v2ray-core/v5/app/router/routercommon"
	"google.golang.org/protobuf/proto"
)

func main() {
	privatePath := flag.String("private", "", "path to unpacked geosite_private.txt")
	categoryAdsPath := flag.String("category-ads", "", "path to unpacked geosite_category-ads.txt")
	categoryRuPath := flag.String("category-ru", "", "path to flattened category-ru file from domain-list-community")
	outputPath := flag.String("output", "dist/geosite-compact.dat", "output geosite dat path")

	flag.Parse()

	if *privatePath == "" || *categoryAdsPath == "" || *categoryRuPath == "" {
		log.Fatalf("all of -private, -category-ads, -category-ru must be provided")
	}

	if err := os.MkdirAll(filepath.Dir(*outputPath), 0o755); err != nil {
		log.Fatalf("create output dir: %v", err)
	}

	privateDomains, err := parseDomainFile(*privatePath)
	if err != nil {
		log.Fatalf("parse private: %v", err)
	}
	categoryAdsDomains, err := parseDomainFile(*categoryAdsPath)
	if err != nil {
		log.Fatalf("parse category-ads: %v", err)
	}
	categoryRuDomains, err := parseDomainFile(*categoryRuPath)
	if err != nil {
		log.Fatalf("parse category-ru: %v", err)
	}

	siteList := &routercommon.GeoSiteList{
		Entry: []*routercommon.GeoSite{
			{
				CountryCode: "private",
				Domain:      privateDomains,
			},
			{
				CountryCode: "category-ads",
				Domain:      categoryAdsDomains,
			},
			{
				CountryCode: "category-ru",
				Domain:      categoryRuDomains,
			},
		},
	}

	data, err := proto.Marshal(siteList)
	if err != nil {
		log.Fatalf("marshal GeoSiteList: %v", err)
	}
	if err := os.WriteFile(*outputPath, data, 0o644); err != nil {
		log.Fatalf("write %s: %v", *outputPath, err)
	}

	fmt.Printf("Wrote custom geosite to %s\n", *outputPath)
}

func parseDomainFile(path string) ([]*routercommon.Domain, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var res []*routercommon.Domain
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// отбрасываем хвостовой комментарий, если он есть
		if idx := strings.Index(line, "#"); idx >= 0 {
			line = strings.TrimSpace(line[:idx])
			if line == "" {
				continue
			}
		}

		d, ok := parseDomainRule(line)
		if !ok {
			continue
		}
		res = append(res, d)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return res, nil
}

func parseDomainRule(line string) (*routercommon.Domain, bool) {
	typ := routercommon.Domain_Plain
	value := line

	switch {
	case strings.HasPrefix(line, "regexp:"):
		typ = routercommon.Domain_Regex
		value = strings.TrimSpace(line[len("regexp:"):])
	case strings.HasPrefix(line, "keyword:"):
		typ = routercommon.Domain_Plain
		value = strings.TrimSpace(line[len("keyword:"):])
	case strings.HasPrefix(line, "full:"):
		typ = routercommon.Domain_Full
		value = strings.TrimSpace(line[len("full:"):])
	case strings.HasPrefix(line, "domain:"):
		typ = routercommon.Domain_RootDomain
		value = strings.TrimSpace(line[len("domain:"):])
	default:
		// Без префикса — это поддомен (domain:)
		typ = routercommon.Domain_RootDomain
		value = line
	}

	if value == "" {
		return nil, false
	}
	return &routercommon.Domain{
		Type:  typ,
		Value: value,
	}, true
}

