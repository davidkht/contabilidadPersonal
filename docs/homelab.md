# Homelab — despliegue

Contexto operativo para quien vaya a tocar el servidor. La app de producción **no** es este checkout del PC: corre en otra máquina, con Docker, y su base de datos no está en Git.

## Dónde está

| | |
|---|---|
| Servidor | Homelab en la LAN, `192.168.1.8` (SSH en el puerto 22) |
| Código | `/opt/contabilidadPersonal` |
| URL | `http://192.168.1.8:8000` |
| Remoto | `git@github.com:davidkht/contabilidadPersonal.git` |
| Alias en el servidor | `conta` → `cd /opt/contabilidadPersonal` (en `~/.bashrc`) |

No hay proxy inverso ni HTTPS. El puerto 80 del servidor ya lo usa otro servicio; esta app va en el **8000**. También hay Samba en 139/445: no tocarlo. Si desde la LAN el 8000 no responde, en el servidor: `sudo ufw allow 8000/tcp`.

## Cómo está levantada

Docker Engine y el plugin Compose, del repositorio oficial de Docker. El usuario que entra por SSH está en el grupo `docker`. Hay que correr `./app.sh` **sin sudo**: con sudo el contenedor escribe `data/` como root.

Arranque en segundo plano, con reinicio automático (`restart: unless-stopped`):

```bash
./app.sh server
```

Eso exige un `.env` en el directorio del proyecto (no está en Git). El del servidor quedó así:

```bash
APP_ENV=prod
APP_JWT_SECRET=<secreto generado en el servidor, mínimo 32 caracteres>
APP_BIND=0.0.0.0
APP_PORT=8000
```

`APP_ENV=prod` apaga `/api/docs` y el proceso no arranca si falta `APP_JWT_SECRET`. Esa clave firma los JWT: no va al navegador, no se commitea y no se regenera salvo compromiso. Cambiarla cierra todas las sesiones.

Git en el servidor entra con una deploy key de solo lectura (`~/.ssh/contabilidad_deploy`), registrada en GitHub → Settings → Deploy keys del repo, y apuntada desde `~/.ssh/config` (`Host github.com`, `IdentitiesOnly yes`).

`app.sh` está en Git como archivo normal (`100644`). Un clon nuevo responde `Permission denied` a `./app.sh`; se arregla con `chmod +x app.sh` o con `bash app.sh server`.

## Qué no viaja en Git

`.gitignore` excluye `data/` y `.env`.

| En el servidor | Qué es |
|---|---|
| `data/contabilidad.db` | Base viva. Personas, movimientos, hashes de contraseña, bloqueos. |
| `.env` | `APP_JWT_SECRET` y el resto de la config de prod. |
| `data/credenciales_iniciales.txt` | Texto del primer arranque **de esa** base. Puede estar viejo. |

`databases/deudas.db` sí está en Git. Es la base de la app de escritorio, solo lectura. El arranque la importa **una vez**, y solo si `contabilidad.db` todavía no tiene personas. No es la base de producción.

Historia de esta instalación (noviembre 2026): el primer `./app.sh server` importó `deudas.db` y generó contraseñas nuevas en el servidor. Después se reemplazó `data/contabilidad.db` con la del PC (`scp` hacia `/opt/contabilidadPersonal/data/contabilidad.db`) porque ahí ya estaba el cambio de contraseña de `admin`. Desde ese momento la base del PC copiada es la de producción. El `credenciales_iniciales.txt` que generó el primer arranque del servidor **no corresponde** a esa base: no usarlo.

En la base que quedó:

- `admin` ya cambió la contraseña en el PC. La temporal del archivo de credenciales del PC no sirve.
- El resto de cuentas sigue con la temporal de `data/credenciales_iniciales.txt` **del PC** (el que está en el checkout de desarrollo), y el primer ingreso les pide cambiarla.

No vuelvas a copiar `contabilidad.db` desde el PC salvo que se quiera reemplazar la producción a propósito. Un `scp` posterior pisa movimientos registrados en el servidor.

## Actualizar la app

En el servidor, con el usuario de siempre (no root):

```bash
cd /opt/contabilidadPersonal
./app.sh backup
git pull
chmod +x app.sh
./app.sh server
./app.sh status
```

`./app.sh server` reconstruye la imagen y recrea el contenedor. `data/` y `.env` se quedan. `docker compose restart` solo reinicia el proceso: no toma código nuevo.

Antes de un `git pull`, no borres `data/` ni `.env`. Si el pull se queja de cambios locales en archivos rastreados, resuélvelos; no hagas `git reset --hard` ni `git clean` a ciegas.

Comprobar desde otro equipo de la LAN: abrir `http://192.168.1.8:8000` y entrar.

## Operación

| Comando | Qué hace |
|---|---|
| `./app.sh status` | Si el contenedor está arriba |
| `./app.sh logs` | Logs en vivo |
| `./app.sh backup` | Copia consistente en `data/backup-<fecha>.db` |
| `./app.sh down` | Apaga y quita el contenedor. Los datos siguen en `data/` |
| `./app.sh cli list-users` | Lista cuentas |
| `./app.sh cli reset-password <usuario>` | Contraseña temporal nueva, desbloquea la cuenta y cierra sus sesiones |

Tras 5 intentos fallidos desde la misma IP el login responde `account_locked` durante 15 minutos, aunque la contraseña ya sea la correcta. Ese contador está en memoria: `docker compose restart` (o `./app.sh server`) lo limpia. El bloqueo guardado en la base salta más tarde y lo limpia `reset-password`.

## Qué no hacer

- No commitear `.env`, `data/` ni `credenciales_iniciales.txt`.
- No regenerar `APP_JWT_SECRET` en un despliegue normal.
- No correr `./app.sh` con sudo.
- No tratar `databases/deudas.db` como la base que hay que respaldar o copiar: la que importa es `data/contabilidad.db`.
- No asumir que `./app.sh creds` en el servidor muestra las claves vigentes.
