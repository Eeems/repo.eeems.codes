<?php
  if($_SERVER['SERVER_NAME'] != "" && $_SERVER['SERVER_NAME'] != "repo.eeems.codes"){
    header("Location: https://repo.eeems.codes");
    exit;
  }
  $dbs = glob("*/*.db");
  function has($metadata, $name){
    return strpos($metadata, '%'.strtoupper($name).'%') !== false;
  }
  function get($metadata, $name){
    if(!has($metadata, $name)){
      return '';
    }
    $len = strlen($metadata);
    $pos = strrpos($metadata, '%'.strtoupper($name).'%');
    $linelen = strlen($name) + 3;
    $endpos = $len;
    if(preg_match('/\n\n/', $metadata, $matches, PREG_OFFSET_CAPTURE, $pos + 1) == 1){
      $endpos = $matches[0][1];
    }
    return substr($metadata, $pos + $linelen, $len - $pos - ($len - $endpos) - $linelen);
  }
?>
<html>
  <head>
    <title>Eeems' Pacman Repos</title>
    <style>
      html, body {
        margin: 0;
        padding: 0;
      }
      article {
        padding: 1rem;
      }
      article > section {
        width: 100%;
        overflow-x: hidden;
      }
      article > section > aside {
        width: calc(40% - 1rem);
        padding: 0.5rem;
        float: right;
      }
      article > section:after {
        content: "";
        clear: both;
        display: table;
      }
      article > section > p {
        float: left;
        width: 60%;
        font-family: 'Fira Sans', sans-serif;
      }
      article > section pre {
        white-space: pre-wrap;
        overflow: auto;
      }
      article > section code, article > section pre {
        background-color: #eee;
        border-radius: 3px;
        font-family: courier, monospace;
        padding: 0 3px;
      }
      article > section > aside > table pre {
        margin: 0;
      }
      article > section > h3 > a {
        color: black;
        text-decoration: none;
      }
    </style>
  </head>
  <body>
    <article>
      <nav>
        <ol>
          <li><a href="#installation">Installation</a></li>
          <li>
            <a href="#repositories">Repositories</a>
            <ol>
              <?php foreach($dbs as $path) { ?>
                <?php $name = dirname($path); ?>
                <li><a href="#<?=$name?>"><?=$name?></a></li>
              <?php } ?>
            </ol>
          </li>
        </ol>
      </nav>
      <section id="installation">
        <h1>Installation</h2>
        <ul>
          <li>
            Import the base signing key
            <pre><?php
              echo "sudo pacman-key --recv A64228CCD26972801C2CE6E3EC931EA46980BA1B --keyserver keyserver.ubuntu.com\n";
              echo "sudo pacman-key --lsign A64228CCD26972801C2CE6E3EC931EA46980BA1B";
            ?></pre>
          </li>
          <li>
            Install full keychain
            <pre><?php
              echo "sudo pacman -U <a href=\"https://repo.eeems.codes/eeems-keyring.tar.zst\">https://repo.eeems.codes/eeems-keyring.tar.zst</a>";
            ?></pre>
          </li>
          <li>
            Append to <code>/etc/pacman.conf</code>
            <pre><?php
              foreach($dbs as $path) {
                $name = dirname($path);
                echo "[".$name."]\n";
                echo "Server = https://repo.eeems.website/\$repo\n";
                echo "Server = https://repo.eeems.codes/\$repo\n";
                echo "\n";
              }
            ?></pre>
          </li>
          <li>
            Resync databases and update installed packages
            <pre><?php
              echo "sudo pacman -Syu";
            ?></pre>
          </li>
        </ul>
        <p>
          If you encounter any issues, please report them <a href="https://eeems.codes/Eeems/repo.eeems.codes/issues">here</a> or to <a href="mailto://repo@eeems.codes">repo@eeems.codes</a>
        </p>
      </section>
    </article>
    <h1 id="repositories">Repositories</h1>
    <?php foreach($dbs as $path) { ?>
      <?php $db = scandir('phar://'.$path); ?>
      <?php $name = dirname($path); ?>
      <article id="<?=$name?>">
        <h2><?=$name?></h1>
        <?php foreach($db as $file) { ?>
          <?php $metadata = file_get_contents('phar://'.$path.'/'.$file.'/desc'); ?>
          <?php $pkgname = get($metadata, 'name'); ?>
          <section>
            <h3 id="package-<?=$pkgname?>">
              <?=$pkgname?>
              <a href="#package-<?=$pkgname?>">⚓</a>
            </h3>
            <aside>
              <table>
                <?php if(has($metadata, 'md5sum')){ ?>
                  <tr>
                    <td>MD5</td>
                    <td><pre><?=get($metadata, 'md5sum')?></pre></td>
                  </tr>
                <?php } ?>
                <?php if(has($metadata, 'sha256sum')){ ?>
                  <tr>
                    <td>SHA256</td>
                    <td><pre><?=get($metadata, 'sha256sum')?></pre></td>
                  </tr>
                <?php } ?>
                <?php if(has($metadata, 'pgpsig')){ ?>
                  <tr>
                    <td>PGP</td>
                    <td><pre><?=get($metadata, 'pgpsig')?></pre></td>
                  </tr>
                <?php } ?>
              </table>
            </aside>
            <p>
              <sub>
                <b>Version</b>: <?=get($metadata, 'version')?>
                <?php $license = get($metadata, 'license') ?>
                <b>License</b>: <?=$license?>
                <b>Architecture</b>: <?=get($metadata, 'arch')?>
                <br/>
                <?php if(has($metadata, 'url')){ ?>
                  <a href="<?=get($metadata, 'url')?>">Website</a>
                <?php } ?>
                <?php if($filename){ ?>
                  <a href="<?=$name.'/'.$filename?>">Download</a>
                <?php } ?>
              </sub>
            </p>
            <p>
              <?=get($metadata, 'desc')?>
            </p>
          </section>
        <?php } ?>
      </article>
    <?php } ?>
  </body>
</html>
