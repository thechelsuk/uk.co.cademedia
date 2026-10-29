# frozen_string_literal: true

# Build details for the footer: site.build.sha (6 characters), the full
# commit, and a link to it. In GitHub Actions the
# commit comes from git (or GITHUB_SHA); otherwise "local".
module CadeBuild
  class Generator < Jekyll::Generator
    safe true
    priority :highest

    def generate(site)
      # The checked-out commit first: after a feed update the deploy builds a
      # newer commit than the GITHUB_SHA that started the run.
      sha = `git -C "#{site.source}" rev-parse HEAD 2>/dev/null`.strip
      sha = ENV["GITHUB_SHA"].to_s if sha.empty?
      repo = ENV["GITHUB_REPOSITORY"].to_s
      server = ENV.fetch("GITHUB_SERVER_URL", "https://github.com")

      site.config["build"] = {
        "sha" => sha.empty? ? "local" : sha[0, 6],
        "commit" => sha,
        "url" => (!sha.empty? && !repo.empty?) ? "#{server}/#{repo}/commit/#{sha}" : nil
      }
    end
  end
end
