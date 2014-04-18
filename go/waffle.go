package main

import (
	"flag"
	"fmt"
	"github.com/mattn/go-xmpp"
	"log"
	"os"
	"strings"
    "regexp"
    "net/http"
    "io"
    "io/ioutil"
    "code.google.com/p/go.net/html"
    "bytes"    
)

var server = flag.String("server", "ahe2:5222", "server")
var username = flag.String("username", "waffle@ahe1", "username")
var password = flag.String("password", "nutella", "password")
var notls = flag.Bool("notls", true, "No TLS")
var debug = flag.Bool("debug", false, "debug output")
var room = flag.String("room", "enabledecoding", "room")

var conference = "@conference.ahe1"
var channel = make(chan string)

go func() {
    list.Sort()
    c <- 1  // Send a signal; value does not matter.
}()
doSomethingForAWhile()


func DoSay(talk *xmpp.Client, w string) {
    talk.Send(xmpp.Chat{Remote: *room + conference, Type: "groupchat", Text: w})
}

func say(talk *xmpp.Client, w string) {
    ctalk.Send(xmpp.Chat{Remote: *room + conference, Type: "groupchat", Text: w})
}

func findTitle(data []byte) string {
    root, err := html.Parse(bytes.NewReader(data))
    if err != nil {
        log.Fatal(err)
    }

    path := []string{"html", "head", "title"}
    
    var f func(depth int, n *html.Node) string
    f = func(depth int, n *html.Node) string {
        //~ fmt.Printf("depth: %v\n", depth)
        for c := n.FirstChild; c != nil; c = c.NextSibling {
            if depth < len(path) {
                if  c.Type == html.ElementNode {
                    //~ fmt.Printf("element: %v\n", c.Data)
                    if c.Data == path[depth] {
                        return f(depth + 1, c)
                    }
                }
            } else if c.Type == html.TextNode {
                return c.Data
            }
		}
        return ""
    }
    
    return f(0, root);
}

func main() {
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: example [options]\n")
		flag.PrintDefaults()
		os.Exit(2)
	}

	flag.Parse()
	if *username == "" || *password == "" {
		flag.Usage()
	}

	var talk *xmpp.Client
	var err error
	if *notls {
		talk, err = xmpp.NewClientNoTLS(*server, *username, *password, *debug)
	} else {
        talk, err = xmpp.NewClient(*server, *username, *password, *debug)
	}

	if err != nil {
		log.Fatal(err)
	}

	talk.JoinMUC(*room + conference + "/waffle")
    
    for {
        chat, err := talk.Recv()
        if err != nil {
            log.Fatal(err)
        }
        switch v := chat.(type) {
        case xmpp.Chat:
            fmt.Printf("message from %s: %s\n" ,v.Remote, v.Text);
            re := regexp.MustCompile(`http[s]?:\/\/[^ ]*`)
            m := re.FindAllStringSubmatch(v.Text, -1)
            for i := range m {
                fmt.Printf("match %v\n", m[i][0])
                resp, err := http.Get(m[i][0])
                if err != nil {
                    log.Fatal(err)
                }
                defer resp.Body.Close()
                
                if resp.StatusCode != 200 {
                    say(talk, "HTTP error: " + string(resp.StatusCode));
                }
                
                limitReader := io.LimitReader(resp.Body, 512 * 1024)
                data, err := ioutil.ReadAll(limitReader)
                if err != nil {
                    log.Fatal(err)
                }
                
                h := resp.Header["Content-Type"]
                fmt.Printf("Content-Type: %v\n", h);
                if len(h) == 0 {
                    say(talk, "cannot get content type");
                } else if !strings.Contains(h[0], "text/html") {
                    say(talk, "not HTML");
                }

                title := findTitle(data);
                if title == "" {
                    say(talk, "cannot find title");
                } else {
                    say(talk, "Title: " + title);
                }
            }
        case xmpp.Presence:
            fmt.Printf("presence from %s: %s\n" ,v.From, v.Show);
        }
    }
}
