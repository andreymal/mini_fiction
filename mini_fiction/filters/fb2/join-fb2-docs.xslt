<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:fb2="http://www.gribuser.ru/xml/fictionbook/2.0"
    extension-element-prefixes="fb2">
    
    <xsl:import href="fb2-description.xslt"/>
    
<xsl:template match="/">
    <FictionBook xmlns:xlink="http://www.w3.org/1999/xlink">
        <xsl:call-template name="create-fb2-description">
            <xsl:with-param name="annotation" select="(.//fb2:FictionBook)[1]/fb2:description/fb2:title-info/fb2:annotation/node()"/>
        </xsl:call-template>
        <body>
            <xsl:apply-templates select=".//fb2:FictionBook/fb2:body[not(@name)]/*"/>
        </body>
        <body name="notes">
            <xsl:apply-templates select=".//fb2:FictionBook/fb2:body[@name]/*"/>
        </body>
        <xsl:call-template name="create-fb2-footer"/>
    </FictionBook>
</xsl:template>

<xsl:template name="get-id-prefix">
    <xsl:for-each select="ancestor::fb2:FictionBook">
        <xsl:value-of select="concat('doc', count(preceding-sibling::*)+1, '_')"/>
    </xsl:for-each>
</xsl:template>

<xsl:template match="fb2:a/@xlink:href[starts-with(., '#')]">
    <xsl:attribute name="xlink:href">
        <xsl:text>#</xsl:text>
        <xsl:call-template name="get-id-prefix"/>
        <xsl:value-of select="substring-after(., '#')"/>
    </xsl:attribute>
</xsl:template>

<xsl:template match="fb2:section/@id">
    <xsl:attribute name="id">
        <xsl:call-template name="get-id-prefix"/>
        <xsl:value-of select="."/>
    </xsl:attribute>
</xsl:template>

<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>

    
</xsl:stylesheet>