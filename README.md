# Ansible Lookup Plugin - Lastpass

Perform lookups on the entries in your LastPass account.

## Requirements

The LastPass [`lpass`
utility](https://lastpass.github.io/lastpass-cli/lpass.1.html) must be
installed on the control machine.

## Usage

### Setup

In order to perform lookups with this plugin, you *must* have already logged in
to LastPass using `lpass login`.  This plugin will raise an error if it detects
that you are not currently logged in.

### Options

Each lookup must provide as its second argument (after `"lastpass"`) that
represents either the unique ID or unique name of an entry in your LastPass
Vault.  For instance, if you wanted to lookup up data related to your GitHub
account, you might provide the argument `https://github.com` if you are using
the `fixed_strings` option, or just `github.com` if your are using the
`basic_regexp` option.  *NOTE* this plugin raises an exception if the search
string matches more than one entry in your LastPass Vault.

- `basic_regexp`: When true, indicates that the string to match against is a
  regular expression.
- `fixed_strings`: When true, indicates that the string to match against is a
  fixed string.  Lookups will be case-sensitive.
- `expand_multi`: If multiple accounts match the provided string/regular
  expression, expand the result set for all of them.
- `field`: Which field to retrieve.  Any field associated with
  an account is valid here, so if you have created a custom field for
  an account you may specify it here.  Beware: field names other
  than built-in options (i.e., those that correspond to CLI flags
  like `--password`) are case-sensitive.  Built-in choices are:
    - `username`:  The `Username` field associated with an account.
    - `password`:  The `Password` field associated with an account.
    - `url`:  The `URL` field associated with an account.
    - `notes`:  The `notes` field associated with an account.
    - `id`:  The ID of an account.
    - `name`:  The `Name` field associated with an account.
- `as_dict`: Normally, lookups return the content of a single field.  When this
  argument is true, the lookup returns a dictionary mapping field names to
  fields.
- `pairs`: When `as_dict`: is true, returns all fields as a list of hashes
  containing the entries `key` and `value`, much like the `with_dict`
  loop type.
- `sync`: Synchronize with LastPass' servers.  Options are `auto`, `now`, and
  `no`.

## Examples

```yaml
# Look up up the password associated with your http://foo.com account:
- debug: msg='{{ lookup("lastpass", "http://foo.com", field="password") }}'
```

```
ok: [localhost] => {
    "msg": "5053CR37"
}
```

```yaml
# Look up up the username associated with your foo.com account:
- debug: msg='{{ lookup("lastpass", "http://foo.com", field="username") }}'
```

```
ok: [localhost] => {
    "msg": "me"
}
```

```yaml
# Look up up the URL associated with your foo.com account:
- debug: msg='{{ lookup("lastpass", "http://foo.com", field="url") }}'
```

```
ok: [localhost] => {
    "msg": {
        "password": "5053CR37",
        "url": "http://foo.com",
        "username": "me"
    }
}
```

```yaml
# Look up all fields associated with your foo.com account and return them as a
# hash:
- debug: msg='{{ lookup("lastpass", "http://foo.com", as_dict=True) }}'
```

```
ok: [localhost] => {
    "msg": [
        {
            "key": "username",
            "value": "me"
        },
        {
            "key": "url",
            "value": "http://foo.com"
        },
        {
            "key": "password",
            "value": "5053CR37"
        }
    ]
}
```

## Caveats

At present, the `lpass show` command that underpins this plugin cannot be
configured to display results in a standard serialization format like JSON or
YAML.  Instead, it uses an ad-hoc style of one `key: value` pair per line.  It
would be possible to load this as YAML, except that keys and values aren't
quoted, so parsing breaks if any YAML metacharacters appear in either.

For now, this plugin employs a simplistic parser that just splits each line on
the first colon encountered, stripping any leading and trailing whitespace from
the righthand field.  The plugin is therefore unable to handle fields with
colons in their name or surrounding spaces in their value.  For instance:

```yaml
# Given "my: custom: field:"="Hello!"
- debug: '{{ lookup("lastpass", "http://contrived-example.org", as_dict=True, pairs=True) }}'
```

```
ok: [localhost] => {
    "msg": [
        {
            "key": "url",
            "value": "http://contrived-example.org"
        },
        {
            "key": "my",
            "value": "custom: field: Hello!"
        },
    ]
}
```

```yaml
# Given "notes"="    I just need some space    "
- debug: '{{ lookup("lastpass", "http://contrived-example.org", as_dict=True, pairs=True) }}'
```

```
ok: [localhost] => {
    "msg": [
        {
            "key": "url",
            "value": "http://contrived-example.org"
        },
        {
            "key": "notes",
            "value": "I just need some space"
        },
    ]
}
```

Work is currently underway at the [`lastpass-cli`
repo](https://github.com/lastpass/lastpass-cli) to [add support for
output
formatting](https://github.com/lastpass/lastpass-cli/tree/topic-user-format-strings).
A future version of this plugin will incorporate use of this feature.

## License

GPLv3

## Author Information

Matt Schreiber <mschreiber@gmail.com>
